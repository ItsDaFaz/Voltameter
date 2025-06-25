from discord.ext import tasks, commands
from db.models import Guild as DBGuild, Member as DBMember, Message as DBMessage
from sqlalchemy import select, delete
from datetime import datetime, timedelta, timezone
from utils.helpers import async_db_retry
class DBManager(commands.Cog):
    def __init__(self, is_prod, client, SessionLocal):
        self.client = client
        self.is_prod = is_prod
        self.SessionLocal = SessionLocal

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"DBManager is ready. Logged in as {self.client.user}")

    @async_db_retry()
    async def get_guild(self, guild_id):
        async with self.SessionLocal() as session:
            return await session.scalar(select(DBGuild).where(DBGuild.id == guild_id))
    @async_db_retry()
    async def get_member(self, member_id, guild_id):
        async with self.SessionLocal() as session:
            return await session.scalar(select(DBMember).where(DBMember.id == member_id, DBMember.guild_id == guild_id))
    @async_db_retry()
    async def add_message(self, message):
        async with self.SessionLocal() as session:
            db_message = DBMessage(
                id=message.id,
                author_id=message.author.id,
                guild_id=message.guild.id,
                timestamp=message.created_at
            )
            session.add(db_message)
            await session.commit()
    
    @async_db_retry()
    async def get_guild_config(self, guild_id, key=None):
        async with self.SessionLocal() as session:
            db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild_id))
            if not db_guild:
                return None
            configs = db_guild.configs or {}
            if key:
                return configs.get(key)
            return configs

    @async_db_retry()
    async def set_guild_config(self, guild_id, key, value):
        async with self.SessionLocal() as session:
            db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild_id))
            if not db_guild:
                return False
            if db_guild.configs is None:
                db_guild.configs = {}
            db_guild.configs[key] = value
            session.add(db_guild)
            await session.commit()
            return True

    @async_db_retry()
    async def set_guild_configs(self, guild_id, configs_dict):
        async with self.SessionLocal() as session:
            db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild_id))
            if not db_guild:
                return False
            db_guild.configs = configs_dict
            session.add(db_guild)
            await session.commit()
            return True

    @async_db_retry()
    async def add_guild(self, guild):
        try:
            async with self.SessionLocal() as session:
                db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild.id))
                if not db_guild:
                    print(f"Guild {guild.name} ({guild.id}) not found in database, adding it.")
                    id = guild.id
                    name = guild.name
                    default_configs = {
                        "admin_role_id_list": [],
                        "text_channels_list": [],
                        "forum_channels_list": [],
                        "destination_channel_id": None,
                        "destination_channel_id_dev": None,
                        "text_multiplier": 3,
                        "in_voice_boost_multiplier": 2
                    }
                    new_guild = DBGuild(
                        id=id,
                        name=name,
                        configs=default_configs
                    )
                    print("New guild created:", new_guild)
                    session.add(new_guild)
                    await session.commit()
                else:
                    print(f"Guild already exists in DB: {db_guild}")
        except Exception as e:
            print(f"Exception in add_guild: {e}", flush=True)
            # print(traceback.format_exc(), flush=True)

    @tasks.loop(hours=24)
    @async_db_retry()
    async def cleanup_old_messages(self):
        async with self.SessionLocal() as session:
            # Clear messages older than 10 days
            ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
            await session.execute(
                delete(DBMessage).where(DBMessage.timestamp < ten_days_ago)
            )
            await session.commit()
            print("Old messages cleaned up.")