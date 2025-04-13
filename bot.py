from config import *
from discord.ext import tasks
import discord
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional, List, cast
from discord import Guild, TextChannel, Role, Member, Message, Embed, Color, User, Thread
from dotenv import load_dotenv
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

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
    print(f"{client.user} has logged in!")
    auto_leaderboard.start()

@client.event
async def on_message(message):
    if message.author.id != 1117105897710305330:
        pass


@tasks.loop(minutes=5)
async def auto_leaderboard():
    # Constants


    # Guild validation
    guild: Optional[Guild] = client.get_guild(GUILD_ID)
    if not guild:
        print(f"Could not find guild with ID {GUILD_ID}")
        return

    # Channel or thread validation
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

    print(destination_channel)

    if not isinstance(destination_channel, (TextChannel, Thread)):
        print(f"Channel {DESTINATION_CHANNEL_ID} is not a text channel or thread.")
        return

    # Bot user validation
    bot_user: Optional[discord.ClientUser] = client.user
    if not bot_user:
        print("Bot user is not initialized")
        return



    # Message counting
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    text_channels: List[TextChannel] = [
        channel for channel in guild.channels
        if isinstance(channel, TextChannel)
    ]
    count_messages_by_members = Counter()

    for channel in text_channels:
        try:
            channel_messages = []
            async for message in channel.history(limit=None, after=seven_days_ago):
                channel_messages.append(message)
                if message.author and not message.author.bot:
                    count_messages_by_members[message.author] += 1
        except Exception as e:
            print(f"Error processing channel {channel.name}: {e}")
            continue

    # Filter out admin members and get top ten
    non_admin_messages = {}
    for member, count in count_messages_by_members.items():
        if isinstance(member, Member):
            member_role_ids = {role.id for role in member.roles}
            if not member_role_ids.intersection(ADMIN_ROLES_IDS):
                non_admin_messages[member] = count

    top_ten = Counter(non_admin_messages).most_common(10)
    if not top_ten:
        print("No non-admin messages found in the last 7 days")
        return

    # Create embed
    embed = Embed(
        title=EMBED_TITLE,
        description=EMBED_DESCRIPTION,
        color=Color.from_rgb(255, 66, 66)
    )

    top_ten_list: List[int] = []
    embed_content = ""
    for idx, (member, count) in enumerate(top_ten):
        if isinstance(member, Member):
            top_ten_list.append(member.id)
            embed_content += f"{idx}. {member.name} • {count} messages\n"

    if not embed_content:
        print("No valid non-admin members found in top ten")
        return

    # Delete previous bot messages
    try:
        messages: List[Message] = []
        async for message in destination_channel.history(limit=None):
            messages.append(message)
            if message.author == bot_user:
                await message.delete()
    except Exception as e:
        print(f"Error cleaning previous messages: {e}")

    embed.add_field(name="", value=embed_content)
    embed.set_footer(text="© Codebound")
    await destination_channel.send(embed=embed)

    # Role management
    mr_electricity_role: Optional[Role] = discord.utils.get(guild.roles, id=MR_ELECTRICITY_ROLE_ID)
    high_voltage_role: Optional[Role] = discord.utils.get(guild.roles, id=HIGH_VOLTAGE_ROLE_ID)

    if not high_voltage_role or not mr_electricity_role:
        print("Required roles not found")
        return

    # Remove roles from members no longer in top ten
    high_voltage_members = high_voltage_role.members
    for member in high_voltage_members:
        if member.id not in top_ten_list:
            try:
                await member.remove_roles(high_voltage_role)
            except Exception as e:
                print(f"Error removing role from {member.name}: {e}")

    # Add roles to new top ten members
    mr_electricity_flag = True
    for member_id in top_ten_list:
        try:
            member: Optional[Member] = await guild.fetch_member(member_id)
            if not member:
                continue

            await member.add_roles(high_voltage_role)

            # Check for admin roles
            member_role_ids = {role.id for role in member.roles}
            has_admin_role = bool(member_role_ids.intersection(ADMIN_ROLES_IDS))

            if not has_admin_role and mr_electricity_flag:
                await member.add_roles(mr_electricity_role)
                print(f"Awarded Mr. Electricity to {member.name}")
                mr_electricity_flag = False

        except Exception as e:
            print(f"Error handling member {member_id}: {e}")
            continue


@client.tree.command(name="voltage", description="Show voltage leaderboard")
async def voltage(interaction: discord.Interaction):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a guild/server")
        return

    channels = [channel for channel in guild.channels if isinstance(channel, discord.TextChannel)]
    count_messages_by_members = Counter()

    await interaction.response.defer()

    for channel in channels:
        try:
            messages = []
            async for message in channel.history(limit=None, after=seven_days_ago):
                messages.append(message)
                if not message.author.bot:
                    count_messages_by_members[message.author] += 1
        except Exception as e:
            print(f"Error in channel {channel.name}: {e}")
            continue

    # Filter out admin members and get top ten
    non_admin_messages = {}
    for member, count in count_messages_by_members.items():
        if isinstance(member, Member):
            member_role_ids = {role.id for role in member.roles}
            if not member_role_ids.intersection(ADMIN_ROLES_IDS):
                non_admin_messages[member] = count

    top_ten = Counter(non_admin_messages).most_common(10)
    if not top_ten:
        print("No non-admin messages found in the last 7 days")
        return

    # Create embed
    embed = Embed(
        title=EMBED_TITLE,
        description=EMBED_DESCRIPTION,
        color=Color.from_rgb(255, 66, 66)
    )

    top_ten_list: List[int] = []
    embed_content = ""
    for idx, (member, count) in enumerate(top_ten):
        if isinstance(member, Member):
            top_ten_list.append(member.id)
            embed_content += f"{idx}. {member.name} • {count} messages\n"

    if not embed_content:
        print("No valid non-admin members found in top ten")
        return


    embed.add_field(name="", value=embed_content)
    embed.set_footer(text="© Codebound")

    await interaction.followup.send(embed=embed)

if isinstance(TOKEN,str):
    client.run(TOKEN)
else:
    print("TOKEN is required to run the bot")
