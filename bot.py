from config import DESTINATION_CHANNEL_ID,GUILD_ID,MR_ELECTRICITY_ROLE_ID,HIGH_VOLTAGE_ROLE_ID,ADMIN_ROLES_IDS, IN_VOICE_ROLE_ID
from discord.ext import tasks
import discord
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional, List
from discord import Interaction, Guild, TextChannel, Role, Member, Embed, Color, Thread
from dotenv import load_dotenv
import os
import threading
from flask import Flask
import asyncio
import re

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# util to prevent markdown in user names
def escape_markdown(text: str) -> str:
    return re.sub(r'([_*~`|>])', r'\\\1', text)

# Run the web server in a separate thread
threading.Thread(target=run_web).start()

load_dotenv()
TOKEN=os.getenv("TOKEN")
intents = discord.Intents.default()
intents.messages = True
intents.typing = False
intents.presences = False
intents.message_content = True  # This is needed for message content
intents.guild_messages = True
intents.members = True
EMBED_TITLE="High Voltage Leaderboard"
EMBED_COLOR="#FF4242"
EMBED_DESCRIPTION="Most active HLB members are listed below. The board is refreshed every 5 minutes. The staff members are not eligible for High Voltage ranking. This is only for the regular HLB members."
class VoltameterClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = VoltameterClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    if not auto_leaderboard.is_running():
            auto_leaderboard.start()

    for guild in client.guilds:
        role = guild.get_role(IN_VOICE_ROLE_ID)
        if not role:
            print(f"Role ID {IN_VOICE_ROLE_ID} not found in guild: {guild.name}")
            continue

        # Set of all members currently in any voice channel
        members_in_vc = {
            member for vc in guild.voice_channels for member in vc.members
        }

        # Assign role to those in VC
        for member in members_in_vc:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason="In VC at bot startup")
                    print(f"Gave 'In Voice' to {member.name}")
                except Exception as e:
                    print(f"Failed to give role to {member.name}: {e}")

        # Remove role from those *not* in VC but who still have it
        for member in guild.members:
            if role in member.roles and member not in members_in_vc:
                try:
                    await member.remove_roles(role, reason="Not in VC at bot startup")
                    print(f"Removed 'In Voice' from {member.name}")
                except Exception as e:
                    print(f"Failed to remove role from {member.name}: {e}")


@client.event
async def on_message(message):
    if message.author.id != 1117105897710305330:
        pass

# VOICE CHANNEL MANAGEMENT

# detect members joining and leaving voice channels
@client.event
async def on_voice_state_update(member, before, after):
    await asyncio.sleep(2)  # Let Empymanager settle any auto-move

    role = member.guild.get_role(IN_VOICE_ROLE_ID)
    if not role:
        print(f"Role ID {IN_VOICE_ROLE_ID} not found in guild: {member.guild.name}")
        return

    # Member is now in a voice channel
    if member.voice and member.voice.channel:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Joined VC")
                print(f"{member.name} was given 'In Voice' role.")
            except Exception as e:
                print(f"Failed to add role to {member.name}: {e}")
    else:
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Left VC")
                print(f"{member.name} had 'In Voice' role removed.")
            except Exception as e:
                print(f"Failed to remove role from {member.name}: {e}")


async def generate_leaderboard_embed(guild: Guild):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    text_channels: List[TextChannel] = [
        channel for channel in guild.channels
        if isinstance(channel, TextChannel)
    ]
    count_messages_by_members = Counter()

    for channel in text_channels:
        try:
            async for message in channel.history(limit=None, after=seven_days_ago):
                if message.author and not message.author.bot:
                    count_messages_by_members[message.author] += 1
        except Exception as e:
            print(f"Error processing channel {channel.name}: {e}")
            continue

    # Filter out admin members and get top ten
    non_admin_messages = {
        member: count for member, count in count_messages_by_members.items()
        if isinstance(member, Member) and not {role.id for role in member.roles}.intersection(ADMIN_ROLES_IDS)
    }

    top_ten = Counter(non_admin_messages).most_common(10)

    embed = Embed(
        title=EMBED_TITLE,
        description=EMBED_DESCRIPTION,
        color=Color.from_rgb(255, 66, 66)
    )

    embed_content = ""
    top_ten_list = []

    for idx, (member, count) in enumerate(top_ten):
        if isinstance(member, Member):
            memberName= escape_markdown(member.name)
            embed_content += f"`{idx+1}` **{memberName}** — `{count}` messages\n"
            top_ten_list.append(member.id)

    if not embed_content:
        return None, []

    embed.add_field(name="", value=embed_content)
    embed.set_image(url="https://res.cloudinary.com/codebound/image/upload/v1681039731/hlb-post_high-voltage_fhd_v2.1_paegjl.jpg")
    embed.set_thumbnail(url="https://res.cloudinary.com/codebound/image/upload/v1681116021/pfp-hlb-high-voltage_em6tpk.png")
    embed.set_footer(text="© Codebound")

    return embed, top_ten_list



@tasks.loop(minutes=5)
async def auto_leaderboard():
    global cached_leaderboard_embed
    guild: Optional[Guild] = client.get_guild(GUILD_ID)
    if not guild:
        print(f"Could not find guild with ID {GUILD_ID}")
        return

    try:
        destination_channel = await client.fetch_channel(DESTINATION_CHANNEL_ID)
    except discord.NotFound:
        print(f"Channel {DESTINATION_CHANNEL_ID} was not found")
        return
    except discord.Forbidden:
        print(f"Bot does not have permission to access channel {DESTINATION_CHANNEL_ID}")
        return
    except discord.HTTPException as e:
        print(f"HTTP error while fetching channel: {e}")
        return

    if not isinstance(destination_channel, (TextChannel, Thread)):
        print(f"Channel {DESTINATION_CHANNEL_ID} is not a text channel or thread.")
        return

    bot_user: Optional[discord.ClientUser] = client.user
    if not bot_user:
        print("Bot user is not initialized")
        return

    embed, top_ten_list = await generate_leaderboard_embed(guild)

    if not embed:
        print("No valid non-admin members found for leaderboard")
        return

    # Clean previous bot messages
    try:
        async for message in destination_channel.history(limit=None):
            if message.author == bot_user:
                await message.delete()
    except Exception as e:
        print(f"Error cleaning previous messages: {e}")

    # update cached_leaderboard_embed
    cached_leaderboard_embed=embed
    # Send the new leaderboard
    await destination_channel.send(embed=embed)

    # Role management
    mr_electricity_role: Optional[Role] = discord.utils.get(guild.roles, id=MR_ELECTRICITY_ROLE_ID)
    high_voltage_role: Optional[Role] = discord.utils.get(guild.roles, id=HIGH_VOLTAGE_ROLE_ID)

    if not high_voltage_role or not mr_electricity_role:
        print("Required roles not found")
        return

    # Remove High Voltage from users no longer in top 10
    for member in high_voltage_role.members:
        if member.id not in top_ten_list:
            try:
                await member.remove_roles(high_voltage_role)
            except Exception as e:
                print(f"Error removing High Voltage from {member.name}: {e}")

    # Remove Mr. Electricity from users who are either no longer top or now admins
    for member in mr_electricity_role.members:
        role_ids = {role.id for role in member.roles}
        is_admin = bool(role_ids & set(ADMIN_ROLES_IDS))
        if member.id not in top_ten_list or is_admin:
            try:
                await member.remove_roles(mr_electricity_role)
                print(f"Removed Mr. Electricity from {member.name}")
            except Exception as e:
                print(f"Error removing Mr. Electricity from {member.name}: {e}")

    # Assign roles to top 10
    mr_electricity_given = False
    for member_id in top_ten_list:
        try:
            member = await guild.fetch_member(member_id)
            if not member:
                continue

            await member.add_roles(high_voltage_role)

            has_admin = bool({role.id for role in member.roles} & set(ADMIN_ROLES_IDS))

            if not has_admin and not mr_electricity_given:
                await member.add_roles(mr_electricity_role)
                print(f"Awarded Mr. Electricity to {member.name}")
                mr_electricity_given = True
        except Exception as e:
            print(f"Error processing member {member_id}: {e}")

@client.tree.command(name="voltage", description="Show current voltage leaderboard")
async def voltage(interaction: Interaction):
    global cached_leaderboard_embed

    if cached_leaderboard_embed:
        await interaction.response.send_message(embed=cached_leaderboard_embed)
    else:
        await interaction.response.send_message(
            "Leaderboard is not ready yet! Please try again later.",
            ephemeral=True
        )

if isinstance(TOKEN,str):
    client.run(TOKEN)
else:
    print("TOKEN is required to run the bot")
