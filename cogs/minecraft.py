#Module for commands and tasks related to status of HLB's official Minecraft server
import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

from config import MINECRAFT_STATUS_URL, DESTINATION_CHANNEL_ID_DEV

class MinecraftStatusManager(commands.Cog):
    def __init__(self, client):
        self.client = client
        print("[MINECRAFT] Initializing MinecraftStatusManager cog...", flush=True)
        self.server_status_bulletin.start()
        print("[MINECRAFT] Started server_status_bulletin task.", flush=True)

    async def fetch_status_from_api(self):
        print("Fetching Minecraft server status from API...", flush=True)
        try:
            response = requests.get(MINECRAFT_STATUS_URL)
            if response.status_code == 200:
                print("[MINECRAFT] Successfully fetched Minecraft status from API.", flush=True)
                return response.json()
            else:
                print(f"[MINECRAFT] Error fetching Minecraft status: {response.status_code}", flush=True)
                return None
        except Exception as e:
            print(f"[MINECRAFT] Exception occurred while fetching Minecraft status: {e}", flush=True)
            return None
    def generate_status_embed(self, status_data):
        print("[MINECRAFT] Generating status embed...", flush=True)
        try:
            server_status = "Online" if status_data.get("online", False) else "Offline"

            embed = discord.Embed(
                title="HLB Minecraft Server", 
                color=discord.Color.from_str("#55FF55"))
            embed.description = "Here is the current server joining and status info:"
            embed.add_field(name="IP", value=status_data.get("ip", "N/A"), inline=False)
            embed.add_field(name="Port", value=status_data.get("port", "N/A"), inline=False)
            embed.add_field(name="Status", value=server_status, inline=False)
            embed.add_field(name="Online Players", value=status_data.get("players", {}).get("online", 0), inline=False)
            embed.add_field(name="Max Players", value=status_data.get("players", {}).get("max", 0), inline=False)
            # embed.add_field(name="Version", value=status_data.get("version", "N/A"), inline=False)
            embed_player_list=""
            player_list = status_data.get("players", {}).get("list", [])
            if player_list:
                for idx,player in enumerate(player_list):
                    embed_player_list += f"{idx+1}. {player}\n"
            else:
                embed_player_list = "No players online"
            
            embed.add_field(name="Players currently online: ", value=embed_player_list, inline=False)

            embed.set_footer(text="© Codebound")
            return embed
        except Exception as e:
            print(f"[MINECRAFT] Exception in generate_status_embed: {e}", flush=True)
            return None

    @tasks.loop(seconds=5)
    async def server_status_bulletin(self):
        print("[MINECRAFT] Running server_status_bulletin task...", flush=True)
        # HLB Minecraft Server
        # auto task to be sent to text channel every 5 seconds
        destination_channel = await self.client.fetch_channel(DESTINATION_CHANNEL_ID_DEV)
        print(f"[MINECRAFT] Fetched destination channel: {destination_channel}", flush=True)
        status_data = await self.fetch_status_from_api()
        if status_data:
            print("[MINECRAFT] Status data received, updating bulletin...", flush=True)
            embed = self.generate_status_embed(status_data)
            # Try to find an existing message with the same embed title
            async for message in destination_channel.history(limit=10):
                if message.author == self.client.user and message.embeds:
                    if message.embeds[0].title == "HLB Minecraft Server":
                        try:
                            await message.edit(embed=embed)
                            print("[MINECRAFT] Edited existing bulletin message.", flush=True)
                        except discord.Forbidden:
                            print(f"[MINECRAFT] Cannot edit message in {destination_channel.name}, missing permissions.", flush=True)
                        except discord.HTTPException as e:
                            print(f"[MINECRAFT] Failed to edit message: {e}", flush=True)
                        break
                else:
                # No existing message found, send a new one
                    try:
                        await destination_channel.send(embed=embed)
                        print("[MINECRAFT] Sent new bulletin message.", flush=True)
                    except discord.Forbidden:
                        print(f"[MINECRAFT] Cannot send message to {destination_channel.name}, missing permissions.", flush=True)
                    except discord.HTTPException as e:
                        print(f"[MINECRAFT] Failed to send message: {e}", flush=True)
        else:
            print("[MINECRAFT] Failed to fetch Minecraft server status.", flush=True)

    @app_commands.command(name='mcstatus',description='Get the current status of the HLB Minecraft server')
    async def server_status(self, interaction: discord.Interaction):
        print("[MINECRAFT] Received /mcstatus command.", flush=True)
        # Same as server_status_bulletin but will respond to user in the same channel
        await interaction.response.defer(thinking=True)
        status_data = await self.fetch_status_from_api()
        if not status_data:
            print("[MINECRAFT] No status data available for /mcstatus command.", flush=True)
            await interaction.followup.send("Failed to fetch Minecraft server status.")
            return
        embed = self.generate_status_embed(status_data)
        if embed:
            try:
                await interaction.followup.send(embed=embed)
                print("[MINECRAFT] Sent status embed in response to /mcstatus.", flush=True)
            except discord.Forbidden:
                await interaction.followup.send("I do not have permission to send messages in this channel.")
                print("[MINECRAFT] Missing permissions to send embed in /mcstatus.", flush=True)
            await interaction.followup.send("The Minecraft server is currently online.")
        else:
            print("[MINECRAFT] Failed to generate status embed for /mcstatus command.", flush=True)
            await interaction.followup.send("Failed to generate status embed for the Minecraft server.")

async def setup(client):
    await client.add_cog(MinecraftStatusManager(client))
    print("[MINECRAFT] MinecraftStatusManager cog loaded.", flush=True)