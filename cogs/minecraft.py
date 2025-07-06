#Module for commands and tasks related to status of HLB's official Minecraft server
import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

from config import MINECRAFT_STATUS_URL, DESTINATION_CHANNEL_ID_DEV

class MinecraftStatusManager(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.server_status_bulletin.start()

    async def fetch_status_from_api(self):
        try:
            response = requests.get(MINECRAFT_STATUS_URL)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching Minecraft status: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception occurred while fetching Minecraft status: {e}")
            return None
    
    def generate_status_embed(self, status_data):
        server_status = "Online" if status_data.get("online", False) else "Offline"

        embed = discord.Embed(title="HLB Minecraft Server", color=discord.Color.from_str("55FF55"))
        embed.description = "Here is the current server joining and status info:"
        embed.add_field(name="IP", value=status_data.get("ip", "N/A"), inline=False)
        embed.add_field(name="Port", value=status_data.get("port", "N/A"), inline=False)
        embed.add_field(name="Status", value=server_status, inline=False)
        embed.add_field(name="Online Players", value=status_data.get("players", {}).get("online", 0), inline=True)
        embed.add_field(name="Max Players", value=status_data.get("players", {}).get("max", 0), inline=True)
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

    @tasks.loop(seconds=5)
    async def server_status_bulletin(self):
        # HLB Minecraft Server
        # auto task to be sent to text channel every 5 seconds
        destination_channel = await self.client.fetch_channel(DESTINATION_CHANNEL_ID_DEV)
        status_data = await self.fetch_status_from_api()
        if status_data:
            embed = self.generate_status_embed(status_data)
            # Try to find an existing message with the same embed title
            async for message in destination_channel.history(limit=10):
                if message.author == self.client.user and message.embeds:
                    if message.embeds[0].title == "HLB Minecraft Server":
                        try:
                            await message.edit(embed=embed)
                        except discord.Forbidden:
                            print(f"Cannot edit message in {destination_channel.name}, missing permissions.")
                        except discord.HTTPException as e:
                            print(f"Failed to edit message: {e}")
                        break
                else:
                # No existing message found, send a new one
                    try:
                        await destination_channel.send(embed=embed)
                    except discord.Forbidden:
                        print(f"Cannot send message to {destination_channel.name}, missing permissions.")
                    except discord.HTTPException as e:
                        print(f"Failed to send message: {e}")
        else:
            print("Failed to fetch Minecraft server status.")

    @app_commands.command(name='mcstatus',description='Get the current status of the HLB Minecraft server')
    async def server_status(self, interaction: discord.Interaction):
        # Same as server_status_bulletin but will respond to user in the same channel
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        status_data = await self.fetch_status_from_api()
        if not status_data:
            await interaction.followup.send("Failed to fetch Minecraft server status.")
            return
        embed = self.generate_status_embed(status_data)
        try:
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("I do not have permission to send messages in this channel.")
        await interaction.followup.send("The Minecraft server is currently online.")

async def setup(client):
    await client.add_cog(MinecraftStatusManager(client))
    print("MinecraftStatusManager cog loaded.")