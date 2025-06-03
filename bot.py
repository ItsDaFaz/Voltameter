import os
import threading
import discord
from dotenv import load_dotenv
from leaderboard.leaderboard import LeaderboardManager
from db.init_db import init_models
from web.webserver import run_web
from cogs.voice import VoiceCog 
from cogs.commands import CommandCog
from cogs.messages import MessageCog
import time

load_dotenv()
TOKEN = os.getenv("TOKEN")
IS_PROD = os.getenv("ENVIRONMENT") == "PRODUCTION"

print(f"Running in {'production' if IS_PROD else 'development'} mode", flush=True)

intents = discord.Intents.default()
intents.messages = True
intents.typing = False
intents.presences = False
intents.message_content = True
intents.guild_messages = True
intents.members = True
intents.voice_states = True

class VoltameterClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = VoltameterClient()

# Start Flask web server in a separate thread
threading.Thread(target=run_web).start()

# Initialize managers and cogs
leaderboard_manager = LeaderboardManager(client, IS_PROD)
voice_cog = VoiceCog(client, IS_PROD)
command_cog = CommandCog(client, leaderboard_manager, IS_PROD)
message_cog = MessageCog(client, IS_PROD)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if IS_PROD:
        # Start leaderboard tasks if not already running
        if hasattr(leaderboard_manager, "auto_leaderboard") and not leaderboard_manager.auto_leaderboard.is_running():
            leaderboard_manager.auto_leaderboard.start()
            print("Auto leaderboard started")
        if hasattr(leaderboard_manager, "update_leaderboard_days_task") and not leaderboard_manager.update_leaderboard_days_task.is_running():
            await leaderboard_manager.update_leaderboard_days()
            leaderboard_manager.update_leaderboard_days_task.start()
        # Start voice cog tasks if not already running
        if hasattr(voice_cog, "check_vc_task") and not voice_cog.check_vc_task.is_running():
            voice_cog.check_vc_task.start()
            print("Voice channel check task started")


        
    else:
        # Start leaderboard tasks if not already running
        # if hasattr(leaderboard_manager, "auto_leaderboard") and not leaderboard_manager.auto_leaderboard.is_running():
        #     leaderboard_manager.auto_leaderboard.start()
        #     print("Auto leaderboard started")
        # if hasattr(leaderboard_manager, "update_leaderboard_days_task") and not leaderboard_manager.update_leaderboard_days_task.is_running():
        #     await leaderboard_manager.update_leaderboard_days()
        #     leaderboard_manager.update_leaderboard_days_task.start()
        print("Auto leaderboard and voice channel checks are disabled in development mode.")

@client.event
async def on_voice_state_update(member, before, after):
    if IS_PROD:
        await voice_cog.handle_voice_state_update(member, before, after)
    else:
        print("Auto leaderboard and voice channel checks are disabled in development mode.")

@client.event
async def on_message(message):
    if not IS_PROD:
        await message_cog.on_message(message)
    else:
        print("Message processing is disabled in development mode.")

if isinstance(TOKEN, str):
    client.run(TOKEN)
RETRY_DELAY = 60  # seconds

def run_discord_bot():
    attempt = 1
    delay = RETRY_DELAY
    while True:
        try:
            print(f"Attempt {attempt}: Starting Discord client...", flush=True)
            if TOKEN is None:
                print("TOKEN is required to run the bot")
                break
            client.run(TOKEN)
            break
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}", flush=True)
            if "429" in str(e) or "rate limit" in str(e).lower():
                delay = max(delay * 2, 900)  # Exponential backoff, at least 15 minutes
                print(f"Rate limit detected. Backing off for {delay} seconds...", flush=True)
            else:
                delay = RETRY_DELAY
                print(f"Retrying in {delay} seconds...", flush=True)
            time.sleep(delay)
            attempt += 1

if isinstance(TOKEN, str) and TOKEN:
    run_discord_bot()
else:
    print("TOKEN is required to run the bot")