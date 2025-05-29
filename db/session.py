import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

load_dotenv()
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./test.db")


print(f"Using database URL in session: {DB_URL}")  # Debugging line to check the DB_URL
engine = create_async_engine(DB_URL, echo=True, future=True)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False
)

async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session
