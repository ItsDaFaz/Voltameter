import re
import asyncio
import functools
from sqlalchemy.exc import OperationalError, InterfaceError
import asyncpg

# String utility functions
def escape_markdown(text: str) -> str:
    return re.sub(r'([_*~`|>])', r'\\\\1', text)

def bool_parse(value: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower()
        if value in ('true', '1', 'yes'):
            return True
        elif value in ('false', '0', 'no'):
            return False
    raise ValueError(f"Cannot parse '{value}' as a boolean.")

def async_db_retry(max_attempts=3, delay=2):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, InterfaceError, asyncpg.exceptions._base.InterfaceError) as e:
                    last_exc = e
                    print(f"[DB RETRY] Attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            print(f"[DB RETRY] All {max_attempts} attempts failed.")
            if last_exc is not None:
                raise last_exc
            else:
                raise Exception("Database operation failed after all retry attempts, but no exception was captured.")
        return wrapper
    return decorator

def generate_default_guild_configs(guild):
    """
    Generate default config values for a guild using discord.py Guild object.
    - destination_channel_id: system channel if available, else first text channel
    - text_multiplier: 3
    - in_voice_boost_multiplier: 5
    - admin_role_id_list, text_channels_list, forum_channels_list: []
    - destination_channel_id_dev: None
    """
    # Use system channel if available, else first text channel
    destination_channel_id = None
    if getattr(guild, 'system_channel', None):
        destination_channel_id = guild.system_channel.id if guild.system_channel else None
    if not destination_channel_id and guild.text_channels:
        destination_channel_id = guild.text_channels[0].id
    return {
        "admin_role_id_list": [],
        "text_channels_list": [],
        "forum_channels_list": [],
        "destination_channel_id": destination_channel_id,
        "destination_channel_id_dev": None,
        "text_multiplier": 3,
        "in_voice_boost_multiplier": 5
    }


