import asyncio
import discord
from discord.ext import tasks
from config import IN_VOICE_ROLE_ID
class VoiceCog:
    def __init__(self, client, is_prod):
        self.client = client
        self.is_prod = is_prod
        self.check_vc_task = tasks.loop(minutes=1)(self.check_vc)
        self.start_tasks()
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
                    # Start cooldown before removing role
                    async def delayed_remove():
                        await asyncio.sleep(10)
                        # Re-fetch member to get latest state
                        refreshed_member = await member.guild.fetch_member(member.id)
                        print(f"Checking if {refreshed_member.name} is still in VC after cooldown.", flush=True)
                        if not refreshed_member.voice or not refreshed_member.voice.channel:
                            try:
                                await refreshed_member.remove_roles(role, reason="Left VC (after cooldown)")
                                print(f"{refreshed_member.name} had 'In Voice' role removed after cooldown.", flush=True)
                            except Exception as e:
                                print(f"Failed to remove role from {refreshed_member.name}: {e}")
                        else:
                            print(f"{refreshed_member.name} rejoined a VC during cooldown, not removing role.")
                    asyncio.create_task(delayed_remove())
        else:
            print("Auto leaderboard and voice channel checks are disabled in development mode.")

    async def check_vc(self):
        if self.is_prod:
            await self.client.wait_until_ready()
            for guild in self.client.guilds:
                role = guild.get_role(IN_VOICE_ROLE_ID)
                if not role:
                    print(f"Role ID {IN_VOICE_ROLE_ID} not found in guild: {guild.name}", flush=True)
                    continue

                # Get all members currently in any voice channel
                members_in_vc = {member for vc in guild.voice_channels for member in vc.members}

                # Add the role to members in VC who don't have it
                for member in members_in_vc:
                    if member.bot:
                        continue
                    if role not in member.roles:
                        try:
                            await member.add_roles(role, reason="Joined VC (auto-check)")
                            print(f"Added 'In Voice' to {member.name} (in VC, didn't have role)", flush=True)
                        except Exception as e:
                            print(f"Failed to add role to {member.name}: {e}", flush=True)

                # Remove the role from members who have it but are not in VC
                for member in role.members:
                    if member.bot:
                        print(f"{member.display_name} is a bot, removing role.", flush=True)
                        try:
                            await member.remove_roles(role, reason="Bot in VC")
                            print(f"Removed 'In Voice' from {member.name} (bot)", flush=True)
                        except Exception as e:
                            print(f"Failed to remove role from {member.name}: {e}", flush=True)
                        continue
                    if member not in members_in_vc:
                        try:
                            await member.remove_roles(role, reason="Not in voice channel (auto-check)")
                            print(f"Removed 'In Voice' from {member.name} (not in VC)", flush=True)
                        except Exception as e:
                            print(f"Failed to remove role from {member.name}: {e}", flush=True)
            print("Voice channel check completed.", flush=True)
        else:
            print("Auto leaderboard and voice channel checks are disabled in development mode.", flush=True)