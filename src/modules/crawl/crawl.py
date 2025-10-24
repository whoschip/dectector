import requests
import random
import time
import json
import logging  # Import the logging module


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class crawl:
    def __init__(self):
        self.groups = ["35396105", "33904411", "936626246", "8570423", "34816688"]

    def reqgroup(self, group: str | None = None):
        if group is None:
            group = random.choice(
                self.groups
            )  # Choose group each time, for flexibility
        logging.info(f"On {group}")
        try:
            response = requests.get(
                f"https://groups.roproxy.com/v1/groups/{group}/users?limit=10&sortOrder=Asc"
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.text, group  # Return group
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching group users for group {group}: {e}")
            return None, None  # Return None in case of error

    def nextreq(self, cursor, group):
        try:
            response = requests.get(
                f"https://groups.roproxy.com/v1/groups/{group}/users?limit=10&cursor={cursor}"
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(
                f"Error fetching next page of users for group {group} with cursor {cursor}: {e}"
            )
            return None

    def fetch_user_details(self, userId):  # New method to fetch user details
        try:
            response = requests.get(f"https://users.roproxy.com/v1/users/{userId}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching user details for user ID {userId}: {e}")
            return None

    def moderate(self, data, ch):  # Pass ch (NameCheck instance) as an argument
        moderation_results = []
        try:
            json_data = json.loads(data)
            for user_data in json_data.get("data", []):  # Use .get() for safety
                user = user_data.get("user")
                if not user_data.get("isBanned"):
                    if user:
                        username = user.get("name")
                        displayname = user.get("displayName")
                        if username:
                            try:
                                res = ch.check(username, displayname)
                                moderation_results.append(res)
                                logging.info(f"Moderation result for {username}: {res}")
                            except Exception as e:  # Catch exceptions from namecheck
                                logging.error(f"Error checking name {username}: {e}")
                        else:
                            logging.warning("User data missing 'displayName'")
                    else:
                        logging.warning("User data missing 'user'")
                else:
                    logging.warning("User banned. Good job roblox!")

        except (
            json.JSONDecodeError,
            TypeError,
        ) as e:  # Catch json load and type errors
            logging.error(f"Error processing JSON data: {e}")

        return moderation_results  # Return the results

    def moderate_bio(self, data, bio_ch):
        moderation_results = []
        try:
            json_data = json.loads(data)
            for user_data in json_data.get("data", []):
                user = user_data.get("user")
                if not user_data.get("isBanned"):
                    if user:
                        userId = user.get("userId")
                        if userId:
                            user_details = self.fetch_user_details(userId)
                            if user_details:
                                bio = user_details.get("description")
                                name = user_details.get("name")
                                if bio:
                                    try:
                                        res = bio_ch.check(
                                            bio, name
                                        )  # res already has username, label, reason
                                        # add userId to the result dict
                                        res["userId"] = userId
                                        moderation_results.append(res)
                                        logging.info(
                                            f"Moderation result for bio of {name}: {res}"
                                        )
                                    except Exception as e:
                                        logging.error(
                                            f"Error checking bio for user {name}: {e}"
                                        )
                                else:
                                    logging.warning(f"User {name} has no bio")
                            else:
                                logging.warning(
                                    f"Could not fetch user details for user ID {userId}"
                                )
                        else:
                            logging.warning("User data missing 'userId'")
                    else:
                        logging.warning("User data missing 'user'")
                else:
                    logging.warning("User banned. Good job roblox!")

        except (
            json.JSONDecodeError,
            TypeError,
        ) as e:  # Catch json load and type errors
            logging.error(f"Error processing JSON data: {e}")

        return moderation_results  # Return the results
