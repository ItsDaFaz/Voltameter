import requests
import discord
from discord import app_commands, Interaction
from config import CONTROLLER_URL
from typing import Optional

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
