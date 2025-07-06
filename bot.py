import asyncio
import discord
from discord.ext import commands
from web.webserver import app as fastapi_app, webserver
import uvicorn
from dotenv import load_dotenv
import traceback
from config import TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST
import os
import time
import signal
import sys
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

engine = get_engine()
SessionLocal = get_session_maker(engine)

def handle_shutdown(signum, frame):
    print(f"[Signal Handler] Received shutdown signal: {signum}", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    print("[Signal Handler] Shutting down gracefully...", flush=True)
    asyncio.run(bot.close())
    print("[Signal Handler] Shutdown complete.", flush=True)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# Use commands.Bot for extension/cog support
class VoltameterBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        self.is_prod = IS_PROD
        self.SessionLocal = SessionLocal
        # Remove direct manager instantiation; cogs will handle their own setup

    async def setup_hook(self):
        # Load cogs as extensions (all managers are now handled in cogs)
        await self.load_extension('leaderboard.leaderboard')
        await self.load_extension('cogs.commands')
        await self.load_extension('cogs.voice')
        await self.load_extension('cogs.messages')
        await self.load_extension('cogs.db')
        await self.load_extension('cogs.minecraft')
        await self.tree.sync()

bot = VoltameterBot()

# Remove all event handlers except startup logic
# All event logic is now handled in cogs via @commands.Cog.listener()

async def run_web():
    config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def run_bot():
    if not isinstance(TOKEN, str) or not TOKEN:
        raise RuntimeError("TOKEN is required to run the bot")
    await bot.start(TOKEN)

async def main():
    await asyncio.gather(
        run_web(),
        run_bot(),
    )

if __name__ == "__main__":
    asyncio.run(main())