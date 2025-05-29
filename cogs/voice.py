import asyncio
import discord
from discord.ext import tasks
from config import IN_VOICE_ROLE_ID
class VoiceCog:
    def __init__(self, client, is_prod):
        self.client = client
        self.is_prod = is_prod
        self.check_vc_task = tasks.loop(minutes=1)(self.check_vc)

    def start_tasks(self):
        if not self.check_vc_task.is_running():
            self.check_vc_task.start()
            print("Voice channel check task started")

    async def handle_voice_state_update(self, member: discord.Member, before, after):
        if self.is_prod:
            await asyncio.sleep(2)
            if member.bot:
                print(f"{member.display_name} is a bot, ignoring.")
                return
            role = member.guild.get_role(IN_VOICE_ROLE_ID)
            if not role:
                print(f"Role ID {IN_VOICE_ROLE_ID} not found in guild: {member.guild.name}")
                return
            if member.voice and member.voice.channel:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Joined VC")
                        print(f"{member.name} was given 'In Voice' role.")
                    except Exception as e:
                        print(f"Failed to add role to {member.name}: {e}")
            else:
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Left VC")
                        print(f"{member.name} had 'In Voice' role removed.")
                    except Exception as e:
                        print(f"Failed to remove role from {member.name}: {e}")
        else:
            print("Auto leaderboard and voice channel checks are disabled in development mode.")

    async def check_vc(self):
        if self.is_prod:
            await self.client.wait_until_ready()
            print("Checking voice channels...")
            for guild in self.client.guilds:
                role = guild.get_role(IN_VOICE_ROLE_ID)
                if not role:
                    print(f"Role ID {IN_VOICE_ROLE_ID} not found in guild: {guild.name}")
                    continue
                members_in_vc = {
                    member for vc in guild.voice_channels for member in vc.members
                }
                print(f"Members in VC: [{', '.join(f'{member.name} (bot={member.bot})' for member in members_in_vc)}],")
                for member in role.members:
                    if member.bot:
                        print(f"{member.display_name} is a bot, removing role.")
                        try:
                            await member.remove_roles(role, reason="Bot in VC")
                            print(f"Removed 'In Voice' from {member.name}")
                        except Exception as e:
                            print(f"Failed to remove role from {member.name}: {e}")
                    if member not in members_in_vc:
                        try:
                            await member.remove_roles(role, reason="Not in voice channel")
                            print(f"Removed 'In Voice' from {member.name}")
                        except Exception as e:
                            print(f"Failed to remove role from {member.name}: {e}")
        else:
            print("Auto leaderboard and voice channel checks are disabled in development mode.")