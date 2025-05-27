import os
from dotenv import load_dotenv
import databases

load_dotenv()
DB_URL = os.getenv("DB_URL", "postgresql://user:password@localhost:5432/dbname")
database = databases.Database(DB_URL)
