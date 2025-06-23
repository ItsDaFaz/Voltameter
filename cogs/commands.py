import requests
import discord
from discord import app_commands, Interaction, Color
from config import CONTROLLER_URL
from typing import Optional
from config import TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST, DESTINATION_CHANNEL_ID, DESTINATION_CHANNEL_ID_DEV, EMBED_DESCRIPTION, EMBED_TITLE, EMBED_COLOR
from collections import Counter

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
        @self.client.tree.command(name="voltwinners", description="Check the current winners of the High Voltage Leaderboard")
        async def voltwinners(interaction: Interaction):
            await interaction.response.defer(thinking=True)
            try:
                embed =  self.leaderboard_manager.cached_winners_embed
                if embed:
                    pass
                else:
                    
                    await self.leaderboard_manager.update_cached_winners_embed()
                    embed = self.leaderboard_manager.cached_winners_embed
                    
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                print(f"⚠️ Error: {str(e)[:100]}" + ("..." if len(str(e)) > 100 else ""))
                await interaction.response.send_message(
                    "An error occurred while fetching winners. Please try again later.",
                    ephemeral=True
                )
            
        @self.client.tree.command(name="voltstatus", description="Check the voltage generated across channels")
        async def voltstatus(interaction: Interaction):
            if not self.leaderboard_manager.cached_leaderboard_embed:
                await interaction.response.send_message(
                    "Status is not ready yet! Please try again later.",
                    ephemeral=True
                )
                return
            
            guild = interaction.guild
            text_channels = []
            forum_channels = []

            text_channels_count: Counter = await self.leaderboard_manager.get_channel_message_counts(guild)
            forum_channels_count: Counter = await self.leaderboard_manager.get_forum_message_counts(guild)

            if guild is not None:
                print(f"[IN commands.py] Message counts per text channel: {text_channels_count}")
                print(f"[IN commands.py] Message counts per forum channel: {forum_channels_count}")
            else:
                print("Guild is None, cannot print message counts.")
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True
                )
                return

            for channel_id in TEXT_CHANNEL_LIST:
                channel = guild.get_channel(channel_id) if guild is not None else None
                count:int = text_channels_count.get(channel_id, 0)
                if channel:
                    text_channels.append(f"<#{channel_id}> — `{count*3}` volt generated")
                else:
                    text_channels.append(f"`{channel_id}` (not found) — `{count*3}` volt generated")

            for forum_id in FORUM_CHANNEL_LIST:
                channel = guild.get_channel(forum_id) if guild is not None else None
                count:int = forum_channels_count.get(forum_id, 0)
                if channel:
                    forum_channels.append(f"<#{forum_id}> — `{count*3}` volt generated")
                else:
                    forum_channels.append(f"`{forum_id}` (not found) — `{count}` volt generated")

            embed = discord.Embed(
            title="Volt Status",
            color=Color.from_str(EMBED_COLOR)
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
            embed.add_field(
                name='',
                value=f"\nBased on last `{str(await self.leaderboard_manager.get_leaderboard_days())}` **days** of messaging activities."
            )
            embed.set_footer(text="© Codebound")

            await interaction.response.send_message(embed=embed)
            
        @self.client.tree.command(name="voltify", description="Summon a music bot to your current voice channel or a specified one")
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
