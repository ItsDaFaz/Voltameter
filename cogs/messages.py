import asyncio
from discord.ext import tasks
from config import IN_VOICE_ROLE_ID
from discord import Client, Guild, Member, Message, Role
from db.models import Member as DBMember, Message as DBMessage, Guild as DBGuild
from sqlalchemy import select
from datetime import datetime, timezone
from utils.helpers import async_db_retry

class MessageCog:
    def __init__(self, client, is_prod, SessionLocal):
        
        self.client = client
        self.is_prod = is_prod
        self.SessionLocal = SessionLocal
        
    @async_db_retry()
    async def on_message(self, message: Message):
        if self.is_prod: 
            author = message.author
            in_voice = isinstance(author, Member) and author.get_role(IN_VOICE_ROLE_ID) is not None
            if author.bot:
                return
            
            # If member has the IN_VOICE_ROLE_ID
            if in_voice:
                # Database logic: record every message
                async with self.SessionLocal() as session:
                    try:
                        if isinstance(message.guild, Guild):
                            # Ensure guild exists
                            print(f"Checking for guild in DB: id={message.guild.id}, name={message.guild.name}", flush=True)
                            db_guild = await session.scalar(select(DBGuild).where(DBGuild.id == message.guild.id))
                            if not db_guild:
                                print(f"Guild not found, creating: id={message.guild.id}, name={message.guild.name}", flush=True)
                                db_guild = DBGuild(id=message.guild.id, name=message.guild.name)
                                session.add(db_guild)
                                try:
                                    await session.commit()
                                    print(f"Guild added to DB: {db_guild}", flush=True)
                                except Exception as e:
                                    print(f"Error adding guild: {e}", flush=True)
                                    await session.rollback()
                            else:
                                print(f"Guild already exists in DB: {db_guild}", flush=True)
                        else:
                            print(f"Message from {author.name} in a DM or group chat, skipping.", flush=True)
                            return
                        # Ensure member exists
                        print(f"Checking for member in DB: id={author.id}, guild_id={message.guild.id}", flush=True)
                        db_member = await session.scalar(select(DBMember).where(DBMember.id == author.id))
                        if not db_member:
                            print(f"Member not found, creating: id={author.id}, guild_id={message.guild.id}", flush=True)
                            db_member = DBMember(id=author.id, guild_id=message.guild.id)
                            session.add(db_member)
                            try:
                                await session.commit()
                                print(f"Member added to DB: {db_member}", flush=True)
                            except Exception as e:
                                print(f"Error adding member: {e}", flush=True)
                                await session.rollback()
                        else:
                            print(f"Member already exists in DB: {db_member}", flush=True)
                        # Insert message
                        print(f"Adding message to DB: author_id={author.id}, guild_id={message.guild.id}", flush=True)
                        db_message = DBMessage(
                            author_id=author.id,
                            timestamp=datetime.now(tz=timezone.utc),
                            guild_id=message.guild.id if message.guild else None,
                        )
                        session.add(db_message)
                        try:
                            await session.commit()
                            print(f"Message added to DB: {db_message}", flush=True)
                        except Exception as e:
                            print(f"Error adding message: {e}", flush=True)
                            await session.rollback()
                    except Exception as e:
                        print(f"DB error: {e}", flush=True)
                        await session.rollback()
                        print(f"Message from {author.name}, In Voice: {in_voice}",flush=True)
        else:
            print("Message processing is disabled in development mode.")
            
    @async_db_retry()
    async def on_message_delete(self, message: Message):
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