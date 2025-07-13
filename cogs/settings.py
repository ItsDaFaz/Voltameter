import discord
from discord.ext import commands
from db.models import Guild as DBGuild
from utils.helpers import generate_default_guild_configs
from typing import Any, Dict, Optional
import asyncio
from discord import app_commands
from config import EMBED_COLOR
from cogs.db import DBManager
class SettingsSelect(discord.ui.Select):
    def __init__(self, configs: Dict[str, Any]):
        options = [
            discord.SelectOption(label="Destination Channel", value="destination_channel_id"),
            discord.SelectOption(label="Text Multiplier", value="text_multiplier"),
            discord.SelectOption(label="In-Voice Multiplier", value="in_voice_boost_multiplier"),
            # Add more options as needed
        ]
        super().__init__(placeholder="Choose a setting to configure...", min_values=1, max_values=1, options=options)
        self.configs = configs

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        # Defensive: check for message and embeds
        embed: Optional[discord.Embed] = None
        if interaction.message and getattr(interaction.message, "embeds", None):
            if len(interaction.message.embeds) > 0:
                embed = interaction.message.embeds[0].copy()
        if embed is None:
            embed = discord.Embed(title="Guild Settings", color=discord.Color.blurple())
        # Defensive: get config values safely
        dest_channel = self.configs.get('destination_channel_id')
        text_mult = self.configs.get('text_multiplier')
        voice_mult = self.configs.get('in_voice_boost_multiplier')
        if selected == "destination_channel_id":
            embed.description = (
                f"**Destination Channel**\nCurrent: <#{dest_channel if dest_channel else 'Not set'}>\nSelect a new channel below."
            )
            # You could add a channel select here
        elif selected == "text_multiplier":
            embed.description = (
                f"**Text Multiplier**\nCurrent: `{text_mult if text_mult is not None else 'Not set'}`\nUse a command or button to change."
            )
        elif selected == "in_voice_boost_multiplier":
            embed.description = (
                f"**In-Voice Multiplier**\nCurrent: `{voice_mult if voice_mult is not None else 'Not set'}`\nUse a command or button to change."
            )
        # Defensive: ensure view is present
        view = self.view if self.view else None
        await interaction.response.edit_message(embed=embed, view=view)

class SettingsView(discord.ui.View):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(timeout=None)
        self.add_item(SettingsSelect(config))

class SettingsCog(commands.Cog):
    def __init__(self, client, db_manager: Any):
        self.client = client
        self.db_manager = db_manager
       
    @app_commands.command(name="settings", description="Post the interactive settings menu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_command(self, interaction: discord.Interaction):
        pass
        # if not interaction.guild:
        #     await interaction.response.send_message("This command can only be used in a server (guild) context.", ephemeral=True)
        #     return
        # db_guild = await self.db_manager.get_guild(interaction.guild.id)
        # config = db_guild.configs if db_guild and db_guild.configs else generate_default_guild_configs(interaction.guild)
        # dest_channel = config.get('destination_channel_id')
        # text_mult = config.get('text_multiplier')
        # voice_mult = config.get('in_voice_boost_multiplier')
        # embed = discord.Embed(
        #     title="Guild Settings",
        #     description="Use the dropdown below to configure settings.\n\n"
        #                 f"**Destination Channel:** <#{dest_channel if dest_channel else 'Not set'}>\n"
        #                 f"**Text Multiplier:** `{text_mult if text_mult is not None else 'Not set'}`\n"
        #                 f"**In-Voice Multiplier:** `{voice_mult if voice_mult is not None else 'Not set'}`\n",
        #     color=discord.Color.blurple()
        # )
        # view = SettingsView(config)
        # await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(client):
    
    db_manager = client.get_cog("DBManager")
    await client.add_cog(SettingsCog(client, db_manager))
