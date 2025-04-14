from config import DESTINATION_CHANNEL_ID,GUILD_ID,MR_ELECTRICITY_ROLE_ID,HIGH_VOLTAGE_ROLE_ID,ADMIN_ROLES_IDS
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

# VOICE CHANNEL MANAGEMENT

# detect members joining and leaving voice channels
@client.event
async def on_voice_state_update(member, before, after):
    print("detected vc update")
    if before.channel is None and after.channel is not None:
        print(f"{member.name} joined {after.channel.name}")
    elif before.channel is not None and after.channel is None:
        print(f"{member.name} left {before.channel.name}")
    elif before.channel is not None and after.channel is not None:
        print(f"{member.name} switched from {before.channel.name} to {after.channel.name}")

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
            embed_content += f"{idx}. {member.name} • {count} messages\n"
            top_ten_list.append(member.id)

    if not embed_content:
        return None, []

    embed.add_field(name="", value=embed_content)
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

    # Remove roles from users no longer in top 10
    for member in high_voltage_role.members:
        if member.id not in top_ten_list:
            try:
                await member.remove_roles(high_voltage_role)
            except Exception as e:
                print(f"Error removing High Voltage role from {member.name}: {e}")

    # Assign roles to top 10 members
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
            "Leaderboard is still being compiled. Please try again later.",
            ephemeral=True
        )

if isinstance(TOKEN,str):
    client.run(TOKEN)
else:
    print("TOKEN is required to run the bot")
