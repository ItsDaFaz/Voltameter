import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

load_dotenv(override=True)  # Load environment variables from .env file
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./test.db")

print(f"Using database URL in session: {DB_URL}")  # Debugging line to check the DB_URL

def get_engine():
    return create_async_engine(DB_URL, echo=True, future=True)

def get_session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)

# Usage: create engine and sessionmaker in the thread/event loop where you need them
# Example:
#   engine = get_engine()
#   SessionLocal = get_session_maker(engine)
#   async with SessionLocal() as session:
#       ...
