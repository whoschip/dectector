import time
import random
import logging
import json
import os
from dotenv import load_dotenv

from modules.crawl.crawl import crawl
from modules.biocheck import BioCheck
from modules.db.supabase import SupaDB

load_dotenv()

db = SupaDB(
    os.getenv("SUPBABASE_URL"),
    os.getenv("SUPBASE_SERVICE_KEY"),
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

CHECKPOINT_FILE = "checkpoint.json"


def load_checkpoints(path="checkpoint.json"):
    """
    Load checkpoint file and return a dict mapping group_id -> cursor.
    Supports old format {"cursor": "...", "group": "12345"} by converting it.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    if isinstance(data, dict) and "group" in data and "cursor" in data:
        return {str(data["group"]): data["cursor"]}

    if isinstance(data, dict):
        return {str(k): v for k, v in data.items() if v is not None}

    return {}


def save_checkpoint(cursor, group, path="checkpoint.json"):

    checkpoints = load_checkpoints(path)
    checkpoints[str(group)] = cursor
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoints, f, indent=2, ensure_ascii=False)


def crawl_and_moderate(start_cursor=None, start_group=None):
    ch = BioCheck()
    crawler = crawl()

    if start_group:
        checkpoints = load_checkpoints()
        group_cursor = checkpoints.get(str(start_group))
        if group_cursor:
            logging.info(
                f"Resuming from checkpoint for group {start_group}: cursor={group_cursor}"
            )
            data = crawler.nextreq(group_cursor, start_group)
            group = start_group
            cursor = group_cursor
        else:
            data, group = crawler.reqgroup(start_group)
            cursor = None
    else:
        checkpoints = load_checkpoints()
        groups_list = crawler.groups.copy()
        random.shuffle(groups_list)
        data = None
        group = None
        cursor = None
        for g in groups_list:
            g_cursor = checkpoints.get(str(g))
            if g_cursor:
                logging.info(
                    f"Found checkpoint for group {g}, resuming from cursor {g_cursor}"
                )
                data = crawler.nextreq(g_cursor, g)
                group = g
                cursor = g_cursor
                break
        if data is None:
            # no checkpoints found or resume failed; just request a random group
            data, group = crawler.reqgroup()
            cursor = None

    try:
        # Initialize stats counters
        stats = {"appropriate": 0, "needs review": 0, "inappropriate": 0, "error": 0}
        while True:
            moderation_results = crawler.moderate_bio(data, ch)
            # Count labels
            for x in moderation_results:
                label = x.get("label", "")
                if label in stats:
                    stats[label] += 1
            filtered = [
                {
                    "username": x.get("username", ""),
                    "userid": x.get("userId", ""),
                    "reason": x.get("reason", ""),
                }
                for x in moderation_results
                if x.get("label", "") not in ["appropriate", "error"]
            ]

            if filtered:
                try:
                    db.insert("review", filtered)
                    logging.info(f"Inserted {len(filtered)} rows into review")
                except Exception as e:
                    logging.error(f"Failed to insert rows: {e}")
            else:
                logging.info("No filtered rows to insert, skipping insert.")


            try:

                existing_stats = db.select("stats", {"group": group})
                if existing_stats and len(existing_stats) > 0:
                    row = existing_stats[0]
                    updated_row = {
                        "group": group,
                        "appropriate": row.get("appropriate", 0) + stats["appropriate"],
                        "needs_review": row.get("needs_review", 0)
                        + stats["needs review"],
                        "inappropriate": row.get("inappropriate", 0)
                        + stats["inappropriate"],
                        "error": row.get("error", 0) + stats["error"],
                    }
                    db.update("stats", updated_row, {"group": group})
                    logging.info(f"Stats updated for group {group}: {updated_row}")
                else:
                    stats_row = {
                        "group": group,
                        "appropriate": stats["appropriate"],
                        "needs_review": stats["needs review"],
                        "inappropriate": stats["inappropriate"],
                        "error": stats["error"],
                    }
                    db.insert("stats", [stats_row])
                    logging.info(f"Stats saved for group {group}: {stats_row}")
            except Exception as e:
                logging.error(f"Failed to insert/update stats: {e}")

            try:
                if not data:
                    logging.error("No data returned, stopping.")
                    break
                if isinstance(data, dict):
                    json_data = data
                else:
                    json_data = json.loads(data)
                cursor = json_data.get("nextPageCursor")
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Error getting next cursor: {e}")
                break

            if not cursor:
                logging.info("No more pages.")
                break

            time.sleep(0.5)
            data = crawler.nextreq(cursor, group)
            if data is None:
                break
    except KeyboardInterrupt:
        print("\n⚠️ stopped by user.")
        save_checkpoint(cursor, group)
        return cursor, group

    save_checkpoint(cursor, group)
    return cursor, group


if __name__ == "__main__":
    checkpoints = load_checkpoints()
    last_cursor = None
    last_group = None
    if checkpoints:
        # pick a random group to resume from (migrated checkpoint mapping)
        last_group = str(random.choice(list(checkpoints.keys())))
        last_cursor = checkpoints.get(last_group)
        logging.info(
            f"Resuming from checkpoint ✅ cursor: {last_cursor}, group: {last_group}"
        )
    else:
        logging.info("No checkpoint found, starting fresh.")

    last_cursor, last_group = crawl_and_moderate(last_cursor, last_group)
