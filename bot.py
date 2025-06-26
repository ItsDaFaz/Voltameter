import asyncio
import discord
from web.webserver import app as fastapi_app, webserver  # Ensure 'app' is the FastAPI instance, not the module
import uvicorn
from dotenv import load_dotenv
from leaderboard.leaderboard import LeaderboardManager
import traceback
# Importing cogs
from cogs.voice import VoiceCog 
from cogs.commands import CommandCog
from cogs.messages import MessageCog
from cogs.db import DBManager

from config import TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST

import os
import time
import signal
import sys

# Database imports
from db.init_db import init_models
from db.session import get_engine, get_session_maker
from db.models import Guild as DBGuild
from sqlalchemy import select

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

def handle_shutdown(signum, frame):
    print(f"[Signal Handler] Received shutdown signal: {signum}", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    print("[Signal Handler] Shutting down gracefully...", flush=True)
    asyncio.run(client.close())
    print("[Signal Handler] Shutdown complete.", flush=True)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

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
webserver.set_leaderboard_manager(leaderboard_manager)  # Set the leaderboard manager for the webserver
voice_cog = VoiceCog(client, IS_PROD)
command_cog = CommandCog(client, leaderboard_manager, IS_PROD)
message_cog = MessageCog(client, IS_PROD, SessionLocal)
db_manager = DBManager(client, IS_PROD, SessionLocal)
@client.event
async def on_ready():
    print("=== on_ready START ===", flush=True)
    print(f"Logged in as {client.user}")
    # Check if client.guilds contains guilds not registered in the database
    try:
        for guild in client.guilds:
            await db_manager.add_guild(guild)
    except Exception as e:
        print(f"Exception in on_ready: {e}", flush=True)
        # print(traceback.format_exc(), flush=True)
    print("Attempting to start check_vc", flush=True)
    try:
        print(f"type of voice_cog.check_vc: {type(voice_cog.check_vc)}", flush=True)
        print(f"is_running: {getattr(voice_cog.check_vc, 'is_running', lambda: 'N/A')()}", flush=True)
        voice_cog.check_vc.start() # type: ignore
        print("Voice channel check task started", flush=True)
    except Exception as e:
        print(f"Error starting voice channel check task: {e}", flush=True)
        traceback.print_exc()
    print("Attempting to start auto_leaderboard", flush=True)
    if hasattr(leaderboard_manager, "auto_leaderboard") and not leaderboard_manager.auto_leaderboard.is_running(): # type: ignore
        try:
            leaderboard_manager.auto_leaderboard.start() # type: ignore
            print("Auto leaderboard started")
        except Exception as e:
            print(f"Error starting auto leaderboard: {e}", flush=True)
    
    if hasattr(leaderboard_manager, "update_leaderboard_days_task") and not leaderboard_manager.update_leaderboard_days_task.is_running(): # type: ignore
        try:
            leaderboard_manager.update_leaderboard_days_task.start() # type: ignore
            print("Update leaderboard days task started")
        except Exception as e:
            print(f"Error starting update leaderboard days task: {e}", flush=True)
    if hasattr(leaderboard_manager,"auto_winner") and not leaderboard_manager.auto_winner.is_running(): # type: ignore
        try:
            leaderboard_manager.auto_winner.start() # type: ignore
            print("Auto winner task started")
        except Exception as e:
            print(f"Error starting auto winner task: {e}", flush=True)
    
    if hasattr(db_manager, "cleanup_old_messages_task") and not db_manager.cleanup_old_messages.is_running(): # type: ignore
        try:
            db_manager.cleanup_old_messages.start() # type: ignore
            print("Old messages cleanup task started")
        except Exception as e:
            print(f"Error starting old messages cleanup task: {e}", flush=True)
    print("=== on_ready END ===", flush=True)
@client.event
async def on_guild_join(guild):
    async with SessionLocal() as session:
        try:
            await db_manager.add_guild(guild)
        except Exception as e:
            print(f"Exception in on_guild_join: {e}", flush=True)
            # print(traceback.format_exc(), flush=True)
        
@client.event
async def on_guild_remove(guild):
    async with SessionLocal() as session:
        db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild.id))
        if db_guild:
            print(f"Removing guild {guild.name} ({guild.id}) from database.")
            await session.delete(db_guild)
            await session.commit()
        else:
            print(f"Guild {guild.name} ({guild.id}) not found in database, nothing to remove.")
@client.event
async def on_voice_state_update(member, before, after):
    
    if IS_PROD:
        await voice_cog.handle_voice_state_update(member, before, after)
    else:
        print("Auto leaderboard and voice channel checks are disabled in development mode.")

@client.event
async def on_message(message):
    if IS_PROD:
        channel = message.channel
        # Check if message is in a monitored TextChannel
        if isinstance(channel, discord.TextChannel) and channel.id in TEXT_CHANNEL_LIST:
            print(f"Processing message in TextChannel {channel.name} ({channel.id})", flush=True)
            await message_cog.on_message(message)
        # Check if message is in a thread under a monitored ForumChannel
        elif isinstance(channel, discord.Thread) and channel.parent and channel.parent.id in FORUM_CHANNEL_LIST:
            print(f"Processing message in thread '{channel.name}' under ForumChannel '{channel.parent.name}' ({channel.parent.id})", flush=True)
            await message_cog.on_message(message)
        else:
            print(f"Message in channel {getattr(channel, 'name', str(channel))} ({getattr(channel, 'id', 'unknown')}) is not in the monitored list, skipping.", flush=True)
            return
    else:
        print("Message processing is disabled in development mode.")

@client.event
async def on_message_delete(message):
    if IS_PROD:
        await message_cog.on_message_delete(message)
    else:
        print("Message deletion processing is disabled in development mode.")

async def run_web():
    # If fastapi_app is not the FastAPI instance, import it correctly
    # from web.webserver import app as fastapi_app
    config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=8080, log_level="info")
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