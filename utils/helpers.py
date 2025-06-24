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


