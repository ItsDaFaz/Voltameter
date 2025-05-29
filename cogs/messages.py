import asyncio
from discord.ext import tasks
from config import IN_VOICE_ROLE_ID
from discord import Client, Guild, Member, Message, Role

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
            if isinstance(author, Member) and author.get_role(IN_VOICE_ROLE_ID):
                #insert database command to record message with In Voice role
                
                return
            # Process the message here
            print(f"Message from {author.name}, In Voice: {in_voice}",flush=True)
        else:
            print("Message processing is disabled in development mode.")