import discord
from discord.ext import commands
import os, requests, json
from modules.db.supabase import SupaDB

DISCORD_TOKEN = (
    "MTQyMzUzNjc4MTkxOTM5MTc1NA.GrImtq.qeu1yL10K0sDD9cGlf-7uNC8f799S4r-hvxL5U"
)

SUPABASE_URL = "https://jcklxaqjnfryeoqyjqpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impja2x4YXFqbmZyeWVvcXlqcXBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTQwNTI4OSwiZXhwIjoyMDc0OTgxMjg5fQ.prkePQBRujRGHJvb830-2zIYE90JSg7gm_CT2qOPMOo"
db = SupaDB(SUPABASE_URL, SUPABASE_KEY)

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
    view = ReviewView(r, ctx)
    await ctx.send(embed=embed, view=view)



if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
