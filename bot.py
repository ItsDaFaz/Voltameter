import os
import threading
import discord
from dotenv import load_dotenv
from leaderboard.leaderboard import LeaderboardManager
from web.webserver import run_web
from cogs.voice import VoiceCog 
from cogs.commands import CommandCog

load_dotenv()
TOKEN = os.getenv("TOKEN")
# IS_PROD = os.getenv("ENVIRONMENT") == "PRODUCTION"
IS_PROD = True
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
        print("Auto leaderboard and voice channel checks are disabled in development mode.")

@client.event
async def on_voice_state_update(member, before, after):
    if IS_PROD:
        await voice_cog.handle_voice_state_update(member, before, after)
    else:
        print("Auto leaderboard and voice channel checks are disabled in development mode.")

if isinstance(TOKEN, str):
    client.run(TOKEN)
else:
    print("TOKEN is required to run the bot")