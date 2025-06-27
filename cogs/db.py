from discord.ext import tasks, commands
from db.models import Guild as DBGuild, Member as DBMember, Message as DBMessage
from sqlalchemy import select, delete
from datetime import datetime, timedelta, timezone
from utils.helpers import async_db_retry

class DBManager(commands.Cog):
    def __init__(self, client, is_prod, SessionLocal):
        self.client = client
        self.is_prod = is_prod
        self.SessionLocal = SessionLocal
        self.cleanup_old_messages.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"DBManager is ready. Logged in as {self.client.user}")
        # Register all guilds in DB on startup
        for guild in self.client.guilds:
            await self.add_guild(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.add_guild(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        async with self.SessionLocal() as session:
            db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild.id))
            if db_guild:
                print(f"Removing guild {guild.name} ({guild.id}) from database.")
                await session.delete(db_guild)
                await session.commit()
            else:
                print(f"Guild {guild.name} ({guild.id}) not found in database, nothing to remove.")

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
    async def add_guild(self, guild):
        #Check if client.guilds contains guilds not registered in the database
        try:
            async with self.SessionLocal() as session:
                db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == guild.id))
                if not db_guild:
                    print(f"Guild {guild.name} ({guild.id}) not found in database, adding it.")
                    id = guild.id
                    name = guild.name
                    new_guild = DBGuild(
                        id=id,
                        name=name,
                        admin_role_id_list=[],
                        text_channels_list=[],
                        forum_channels_list=[],
                        destination_channel_id=None,
                        destination_channel_id_dev=None
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

async def setup(client):
    is_prod = getattr(client, 'is_prod', False)
    SessionLocal = getattr(client, 'SessionLocal', None)
    await client.add_cog(DBManager(client, is_prod, SessionLocal))