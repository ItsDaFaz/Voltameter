import requests
import discord
from discord import app_commands, Interaction
from config import CONTROLLER_URL
from typing import Optional
from config import TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST, DESTINATION_CHANNEL_ID, DESTINATION_CHANNEL_ID_DEV, EMBED_DESCRIPTION, EMBED_TITLE, EMBED_COLOR

class CommandCog:
    def __init__(self, client, leaderboard_manager, is_prod):
        self.client = client
        self.leaderboard_manager = leaderboard_manager
        self.is_prod = is_prod
        self.register_commands()

    def register_commands(self):
        @self.client.tree.command(name="voltage", description="Show current voltage leaderboard")
        async def voltage(interaction: Interaction):
            embed = self.leaderboard_manager.cached_leaderboard_embed
            if embed:
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "Leaderboard is not ready yet! Please try again later.",
                    ephemeral=True
                )
        @self.client.tree.command(name="voltcheck", description="Check the current voltage leaderboard")
        async def voltcheck(interaction: Interaction):
            
            # Check if user is administrator
            member = interaction.user
            if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
                await interaction.response.send_message(
                "❌ Only administrators can use this command.",
                ephemeral=True
                )
                return

            guild = interaction.guild
            text_channels = []
            forum_channels = []

            for channel_id in TEXT_CHANNEL_LIST:
                channel = guild.get_channel(channel_id) if guild is not None else None
                if channel:
                    text_channels.append(f"<#{channel_id}>")
                else:
                    text_channels.append(f"`{channel_id}` (not found)")

            for forum_id in FORUM_CHANNEL_LIST:
                channel = guild.get_channel(forum_id) if guild is not None else None
                if channel:
                    forum_channels.append(f"<#{forum_id}>")
                else:
                    forum_channels.append(f"`{forum_id}` (not found)")

            embed = discord.Embed(
                title="Configured Channels",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Text Channels",
                value="\n".join(text_channels) if text_channels else "None",
                inline=False
            )
            embed.add_field(
                name="Forum Channels",
                value="\n".join(forum_channels) if forum_channels else "None",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.client.tree.command(name="voltplay", description="Summon a music bot to your current voice channel or a specified one")
        @app_commands.describe(channel="Summon a music bot to your current voice channel or a specified one")
        async def voltjoin(interaction: Interaction, channel: Optional[discord.VoiceChannel] = None):
            if not self.is_prod:
                try:
                    member = interaction.user
                    if isinstance(member, discord.Member) and member.voice and member.voice.channel:
                        if isinstance(member.voice.channel, discord.VoiceChannel):
                            channel = member.voice.channel
                        else:
                            await interaction.response.send_message(
                                "❌ You must be in a standard voice channel (not a stage channel) or specify one.",
                                ephemeral=True
                            )
                            return
                    else:
                        await interaction.response.send_message(
                            "❌ You must either:\n"
                            "1) Specify a voice channel, or\n"
                            "2) Be in a voice channel when using this command",
                            ephemeral=True
                        )
                        return
                    if interaction.guild is None:
                        await interaction.response.send_message("❌ This command only works in servers.")
                        return
                    payload = {
                        "guild_id": str(interaction.guild.id),
                        "channel_id": str(channel.id)
                    }
                    await interaction.response.defer(thinking=True)
                    response = requests.post(CONTROLLER_URL, json=payload)
                    data = response.json()
                    if response.status_code == 200:
                        if data.get("queued"):
                            await interaction.followup.send("⏳ All bots are busy. Please try again later.")
                        else:
                            await interaction.followup.send(f"🔉 A **VC Hogger** is on its way to **{channel.name}**!")
                    else:
                        await interaction.followup.send("❌ Failed to assign a bot. Please try again later.")
                except Exception as e:
                    print(f"⚠️ Error: {str(e)[:100]}" + ("..." if len(str(e)) > 100 else ""))
                    await interaction.followup.send("Coming Soon!")
            else:
                await interaction.response.send_message(
                    "Coming soon!",
                    ephemeral=True
                )
