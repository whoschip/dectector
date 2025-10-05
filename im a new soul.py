import discord
from discord.ext import commands
from dotenv import load_dotenv
import os, requests, json, time, asyncio
from modules.db.supabase import SupaDB
from modules.crawl.crawl import crawl
from modules.biocheck import BioCheck

load_dotenv()


DISCORD_TOKEN = (
    os.getenv("DISCORD_BOT_TOKEN")
)

SUPABASE_URL = os.get("SUPBABASE_URL")
SUPABASE_KEY = os.get("SUPBASE_SERVICE_KEY")
db = SupaDB(SUPABASE_URL, SUPABASE_KEY)

cl = crawl()
ch = BioCheck()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


class ReviewView(discord.ui.View):
    def __init__(self, review, ctx):
        super().__init__(timeout=None)
        self.review = review
        self.ctx = ctx

    async def show_next_review(self):
        reviews = db.select("review", {})
        if reviews:
            next_review = reviews[0]

            userdecs = fetch_user_details(reviews[0].get("userid", ""))
            if userdecs:
                h = userdecs.get("description", "No description available.")
            else:
                h = "No description available."

            embed = discord.Embed(title="Review Pending", color=discord.Color.orange())
            embed.add_field(
                name="Username", value=next_review.get("username", ""), inline=True
            )
            embed.add_field(
                name="User ID", value=next_review.get("userid", ""), inline=True
            )
            embed.add_field(
                name="Reason", value=next_review.get("reason", ""), inline=False
            )
            embed.add_field(name="User Details", value=str(h), inline=False)
            
            embed.set_thumbnail(url=fetch_user_avatar(next_review.get("userid", "")))


            view = ReviewView(next_review, self.ctx)
            await self.ctx.send(embed=embed, view=view)
        else:
            await self.ctx.send("No more reviews found.")

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        reviewed_entry = {
            "username": self.review.get("username", ""),
            "userid": self.review.get("userid", ""),
            "reason": self.review.get("reason", ""),
        }

        exists = db.select("reviewed", {"userid": reviewed_entry["userid"]})
        if not exists:
            db.insert("reviewed", [reviewed_entry])

        db.delete("review", {"userid": self.review["userid"]})
        await interaction.response.send_message(
            f"Approved review for user {self.review.get('username', '')} (ID: {self.review.get('userid', '')})",
            ephemeral=True,
        )
        await interaction.message.delete()
        await self.show_next_review()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        reviewed_entry = {
            "username": self.review.get("username", ""),
            "userid": self.review.get("userid", ""),
            "reason": self.review.get("reason", ""),
        }

        exists = db.select("reviewed", {"userid": reviewed_entry["userid"]})
        if not exists:
            db.insert("reviewed", [reviewed_entry])
        db.delete("review", {"userid": self.review["userid"]})
        await interaction.response.send_message(
            f"Rejected review for user {self.review.get('username', '')} (ID: {self.review.get('userid', '')})",
            ephemeral=True,
        )
        await interaction.message.delete()
        await self.show_next_review()


def fetch_user_details(userId):
    try:
        response = requests.get(f"https://users.roproxy.com/v1/users/{userId}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user details for user ID {userId}: {e}")
        return None

def fetch_user_avatar(userId):
    try:
        url = f"https://thumbnails.roproxy.com/v1/users/avatar-bust?userIds={userId}&size=352x352&format=Png&isCircular=false"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return None

        item = data[0]
        if item.get("state", "") == "Pending":
            time.sleep(1.5)
            response = requests.get(url)
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                return None
            item = data[0]

        return item.get("imageUrl")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching avatar for user ID {userId}: {e}")
        return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def reviews(ctx):
    """Show the first pending review as an embed with buttons."""
    print("Fetching reviews...")
    reviews = db.select("review", {})
    if not reviews:
        await ctx.send("No reviews found.")
        return

    userdecs = fetch_user_details(reviews[0].get("userid", ""))
    if userdecs:
        h = userdecs.get("description", "No description available.")
    else:
        h = "No description available."

    r = reviews[0]
    embed = discord.Embed(title="Review Pending", color=discord.Color.orange())
    embed.add_field(name="Username", value=r.get("username", ""), inline=True)
    embed.add_field(name="User ID", value=r.get("userid", ""), inline=True)
    embed.add_field(name="Reason", value=r.get("reason", ""), inline=False)
    embed.add_field(name="User Details", value=str(h), inline=False)

    embed.set_thumbnail(url=fetch_user_avatar(r.get("userid", "")))
    view = ReviewView(r, ctx)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def queue(ctx, usr):
    print(f"Queueing user {usr} for review...")
    message = await ctx.send(f"Queueing user {usr} for review...")

    details = await asyncio.to_thread(fetch_user_details, usr)
    if details is None:
        await message.edit(content=f"Failed to fetch details for user {usr}.")
        return

    if isinstance(details, dict):
        username = details.get("name") or details.get("displayName") or details.get("username") or str(usr)
        bio = details.get("description", "") or ""
    else:
        try:
            parsed = json.loads(details)
            username = parsed.get("name") or parsed.get("displayName") or parsed.get("username") or str(usr)
            bio = parsed.get("description", "") or ""
        except Exception:
            username = str(usr)
            bio = ""

    ai_res = await asyncio.to_thread(ch.check, bio, username)
    reason = ai_res.get("reason", "") if isinstance(ai_res, dict) else ""

    try:
        userid_int = int(usr)
    except Exception:
        userid_int = usr

    review_row = {"username": username, "userid": userid_int, "reason": reason}
    exists = db.select("review", {"userid": userid_int})
    if not exists:
        db.insert("review", [review_row])
        await message.edit(content=f"User {usr} queued for review.")
    else:
        await message.edit(content=f"User {usr} is already queued for review.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
