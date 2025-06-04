import asyncio
import discord
from web.webserver import app as fastapi_app
import uvicorn
from dotenv import load_dotenv
from leaderboard.leaderboard import LeaderboardManager
from db.init_db import init_models
from cogs.voice import VoiceCog 
from cogs.commands import CommandCog
from cogs.messages import MessageCog
from db.session import get_engine, get_session_maker
import os
import time

load_dotenv(override=True)
TOKEN = os.getenv("TOKEN")
IS_PROD = os.getenv("ENVIRONMENT") == "PRODUCTION"
print(str(os.getenv("ENVIRONMENT")))
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

engine = get_engine()
SessionLocal = get_session_maker(engine)

# Initialize managers and cogs
leaderboard_manager = LeaderboardManager(client, IS_PROD)
voice_cog = VoiceCog(client, IS_PROD)
command_cog = CommandCog(client, leaderboard_manager, IS_PROD)
message_cog = MessageCog(client, IS_PROD, SessionLocal)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if IS_PROD:
        if hasattr(leaderboard_manager, "auto_leaderboard") and not leaderboard_manager.auto_leaderboard.is_running():
            leaderboard_manager.auto_leaderboard.start()
            print("Auto leaderboard started")
        if hasattr(leaderboard_manager, "update_leaderboard_days_task") and not leaderboard_manager.update_leaderboard_days_task.is_running():
            await leaderboard_manager.update_leaderboard_days()
            leaderboard_manager.update_leaderboard_days_task.start()
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

@client.event
async def on_message(message):
    if not IS_PROD:
        await message_cog.on_message(message)
    else:
        print("Message processing is disabled in development mode.")

async def run_web():
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def run_bot():
    if not isinstance(TOKEN, str) or not TOKEN:
        raise RuntimeError("TOKEN is required to run the bot")
    await client.start(TOKEN)

async def main():
    await asyncio.gather(
        run_web(),
        run_bot(),
    )

if __name__ == "__main__":
    asyncio.run(main())