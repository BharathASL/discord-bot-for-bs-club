import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
import urllib.parse
from discord import app_commands
from flask import Flask
from threading import Thread
import logging

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPERCELL_TOKEN = os.getenv("SUPERCELL_API_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
CLUB_HASH_TAG = os.getenv("CLUB_HASH_TAG")
BS_ROOT_URL = os.getenv("BS_ROOT_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# valid_discord_roles = ["President", "Vice President", "Senior", "Member", "Guest", "Club Member"]
valid_discord_roles_map = {
    "president": ["👑", "👑 President"],
    "vicePresident": ["🔥", "🔥 Vice President"],
    "senior": ["🎓", "🎓 Senior"],
    "member": ["⭐", "⭐ Member"],
    "guest": ["🫂", "🫂 Guest"],
    "clubMember": ["🔰","🔰 Club Member"],
    "unverified": ["❓","❓ Unverified"]
}
valid_discord_role_names = [v[1] for v in valid_discord_roles_map.values()]


bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("discord_bs_register")


class TagModal(discord.ui.Modal, title="Enter Your Brawl Stars Tag"):
    def __init__(self, membership: str):
        super().__init__()
        self.membership = membership  # yes or no
        self.add_item(discord.ui.TextInput(
            label="Brawl Stars Player Tag",
            placeholder="#8LJYQ9U2",
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        logger.info(f"TagModal submitted by {interaction.user} (ID: {interaction.user.id}), membership: {self.membership}")
        await interaction.response.defer(ephemeral=True)
        user_input_tag = f"#{self.children[0].value.strip().replace('#', '').upper()}"
        user_input_is_member = self.membership == "yes"
        user_input_tag_encoded = urllib.parse.quote(user_input_tag)

        # Fetch Brawl Stars data
        headers = {
            "Authorization": f"Bearer {SUPERCELL_TOKEN}"
        }
        res = requests.get(f"https://{BS_ROOT_URL}/v1/players/{user_input_tag_encoded}", headers=headers)

        if res.status_code != 200:
            logger.error(f"API Error {res.status_code}: {res.text}")
            await interaction.followup.send("❌ Invalid player tag or API failure.", ephemeral=True)
            return

        user_data = res.json()
        is_club_member = user_data.get("club", {}).get("tag", "") == CLUB_HASH_TAG

        if user_input_is_member:
            if not is_club_member:
                logger.info(f"User {interaction.user} is not in the club.")
                await interaction.followup.send("❌ You're not in Stellar Forge.", ephemeral=True)
                return

        else:
            if is_club_member:
                logger.info(f"User {interaction.user} said no but is in the club.")
                await interaction.followup.send("❌ You said no, but you're in Stellar Forge.", ephemeral=True)
                return

        # Assign role
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(interaction.user.id)
        
        if is_club_member:
            club_hash_tag_encoded = urllib.parse.quote(CLUB_HASH_TAG)
            res = requests.get(f"https://{BS_ROOT_URL}/v1/clubs/{club_hash_tag_encoded}", headers=headers)
            if res.status_code != 200:
                await interaction.followup.send("❌ API error.", ephemeral=True)
                return

            club_data = res.json()

            member_info = next((m for m in club_data.get("members", []) if m["tag"] == user_input_tag), None)
            if not member_info:
                logger.error("You are not a member of Stellar Forge.")
                await interaction.followup.send("❌ API Error.", ephemeral=True)
                return
            role_name = member_info.get("role")
            if role_name:
                # Assign both the specific club role and the generic club member role
                role_names = [
                    valid_discord_roles_map.get(role_name, ["", role_name])[1],
                    valid_discord_roles_map["clubMember"][1]
                ]
        else:
            role_name = "guest"
            role_names = [valid_discord_roles_map.get("guest")[1]]
        # Convert each element in role_names to a discord role object
        roles = [discord.utils.get(guild.roles, name=rn) for rn in role_names]
        # Filter out None values (roles not found)
        roles = [r for r in roles if r is not None]

        if roles:
            logger.info(f"Assigning roles {[r.name for r in roles]} to {member.name} (ID: {member.id})")
            # Remove all valid Discord roles before assigning the new one
            roles_need_to_remove = [r for r in member.roles if r.name in valid_discord_role_names and r not in roles]
            await member.remove_roles(*roles_need_to_remove)
            await member.add_roles(*roles)
            
            assigned_roles = ', '.join([f"`{r.name}`" for r in roles])
            await interaction.followup.send(
                f"✅ Verification successful! You have been assigned the following role(s): {assigned_roles}. Welcome!",
                ephemeral=True
            )
            
            role_info_strs = valid_discord_roles_map.get(role_name, ["", role_name])
            await member.edit(nick=f"{role_info_strs[0]}{user_data['name']}")
        else:
            logger.warning(f"Role(s) not found for user {member.name} (ID: {member.id})")
            await interaction.followup.send("❌ Role not found. Ask an admin to set up roles.", ephemeral=True)


class MembershipDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Yes", description="I am a member of Stellar Forge", value="yes"),
            discord.SelectOption(label="No", description="I am not a member", value="no")
        ]
        super().__init__(placeholder="Are you a member of Stellar Forge?", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TagModal(membership=self.values[0]))


class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(MembershipDropdown())


@bot.tree.command(
    name="setupregister",
    description="Set up the registration panel for Brawl Stars club members.",
    guild=discord.Object(id=GUILD_ID)
)
# @app_commands.checks.has_permissions(administrator=True)
async def setup_register(interaction: discord.Interaction):
    logger.info(f"setup_register command triggered by {interaction.user} (ID: {interaction.user.id})")
    embed = discord.Embed(
        title="🔐 Register to Access the Server",
        description="Choose your membership status below to start verification.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=DropdownView())


# Sync the slash commands on bot startup
@bot.event
async def on_ready():
    logger.info(f"on_ready triggered. Bot is online. Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")



@bot.event
async def on_member_join(member):
    guild = member.guild
    role_name = valid_discord_roles_map["unverified"][1]
    role = discord.utils.get(guild.roles, name=role_name)
    logger.info(f"on_member_join triggered for {member} (ID: {member.id}) in guild '{guild.name}' (ID: {guild.id})")
    if role:
        await member.add_roles(role)
        logger.info(f"Assigned '{role_name}' role to {member.name} (ID: {member.id})")
    else:
        logger.warning(f"'{role_name}' role not found in guild '{guild.name}' (ID: {guild.id})")


def keep_alive():
    app = Flask('')

    @app.route('/')
    def home():
        return "I'm alive!"

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Suppress request logs

    def run():
        app.run(host='0.0.0.0', port=8080)

    t = Thread(target=run)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)