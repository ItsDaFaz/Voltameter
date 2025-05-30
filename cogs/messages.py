import asyncio
from discord.ext import tasks
from config import IN_VOICE_ROLE_ID
from discord import Client, Guild, Member, Message, Role
from db.session import get_async_session
from db.models import Member as DBMember, Message as DBMessage
from sqlalchemy import select
from datetime import datetime, timezone

class MessageCog:
    def __init__(self, client, is_prod):
        self.client = client
        self.is_prod = is_prod
        
    async def on_message(self, message: Message):
        if not self.is_prod: #Temporarily keep it for development
            author = message.author
            in_voice = isinstance(author, Member) and author.get_role(IN_VOICE_ROLE_ID) is not None
            if author.bot:
                return
            
            #If member has the IN_VOICE_ROLE_ID
            if in_voice:
                # Database logic: record every message
                async for session in get_async_session():
                    # Ensure member exists
                    db_member = await session.scalar(select(DBMember).where(DBMember.id == author.id))
                    if not db_member:
                        db_member = DBMember(id=author.id)
                        session.add(db_member)
                        await session.commit()
                    # Insert message
                    db_message = DBMessage(
                        author_id=author.id,
                        timestamp=datetime.now(tz=timezone.utc),
                    )
                    session.add(db_message)
                    await session.commit()
            print(f"Message from {author.name}, In Voice: {in_voice}",flush=True)
        else:
            print("Message processing is disabled in development mode.")