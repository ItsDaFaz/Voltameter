import asyncio
from discord.ext import tasks, commands
from config import IN_VOICE_ROLE_ID
from discord import Client, Guild, Member, Message, Role
from db.models import Member as DBMember, Message as DBMessage, Guild as DBGuild, member_guild_association
from sqlalchemy import select, delete
from datetime import datetime, timezone
from utils.helpers import async_db_retry
from sqlalchemy.dialects.postgresql import insert

class MessageCog(commands.Cog):
    def __init__(self, client, is_prod, SessionLocal):
        self.client = client
        self.is_prod = is_prod
        self.SessionLocal = SessionLocal

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        await self.handle_on_message(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        await self.handle_on_message_delete(message)

    @async_db_retry()
    async def handle_on_message(self, message: Message):
        if not self.is_prod:
            print("Message processing is disabled in development mode.")
            return

        author = message.author
        if author.bot:
            return

        in_voice = isinstance(author, Member) and author.get_role(IN_VOICE_ROLE_ID) is not None
        if not in_voice:
            return

        async with self.SessionLocal() as session:
            try:
                # Handle guild
                if not isinstance(message.guild, Guild):
                    print(f"Message from {author.name} in a DM or group chat, skipping.", flush=True)
                    return

                print(f"Checking for guild in DB: id={message.guild.id}, name={message.guild.name}", flush=True)
                db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == message.guild.id))
                if not db_guild:
                    print(f"Guild not found, creating: id={message.guild.id}, name={message.guild.name}", flush=True)
                    db_guild = DBGuild(id=message.guild.id, name=message.guild.name)
                    session.add(db_guild)
                    await session.commit()
                    print(f"Guild added to DB: {db_guild}", flush=True)
                else:
                    print(f"Guild already exists in DB: {db_guild}", flush=True)

                # Handle member
                print(f"Checking for member in DB: id={author.id}", flush=True)
                db_member = await session.scalar(select(DBMember).where(DBMember.id == author.id))
                if not db_member:
                    print(f"Member not found, creating: id={author.id}", flush=True)
                    db_member = DBMember(id=author.id)
                    session.add(db_member)
                    await session.flush()  # Ensure member has ID before creating association
                    print(f"Member added to DB: {db_member}", flush=True)

                # Create guild-member association if it doesn't exist
                stmt = insert(member_guild_association).values(
                    member_id=author.id,
                    guild_id=message.guild.id
                ).on_conflict_do_nothing()
                await session.execute(stmt)

                # Insert message
                print(f"Adding message to DB: author_id={author.id}, guild_id={message.guild.id}", flush=True)
                db_message = DBMessage(
                    id=message.id,
                    author_id=author.id,
                    guild_id=message.guild.id,
                    timestamp=message.created_at or datetime.now(tz=timezone.utc)
                )
                session.add(db_message)
                await session.commit()
                print(f"Message added to DB: {db_message}", flush=True)

            except Exception as e:
                print(f"DB error: {e}", flush=True)
                await session.rollback()
                print(f"Message from {author.name}, In Voice: {in_voice}", flush=True)
            
    @async_db_retry()
    async def handle_on_message_delete(self, message: Message):
        if self.is_prod:
            async with self.SessionLocal() as session:
                try:
                    db_message = await session.scalar(select(DBMessage).where(DBMessage.id == message.id))
                    if db_message:
                        await session.delete(db_message)
                        await session.commit()
                        print(f"Deleted message from DB: {db_message}", flush=True)
                    else:
                        print(f"Message not found in DB: id={message.id}", flush=True)
                except Exception as e:
                    print(f"Error deleting message: {e}", flush=True)
                    await session.rollback()
        else:
            print("Message deletion processing is disabled in development mode.")

async def setup(client):
    is_prod = getattr(client, 'is_prod', False)
    SessionLocal = getattr(client, 'SessionLocal', None)
    await client.add_cog(MessageCog(client, is_prod, SessionLocal))