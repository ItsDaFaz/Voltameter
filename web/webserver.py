from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from db.session import database  # Use shared database instance

load_dotenv()  # Load environment variables from .env file
#DB_URL = "postgresql://user:password@localhost:5432/dbname"  # Placeholder
DB_URL = os.getenv("DB_URL", "postgresql://user:password@localhost:5432/dbname")  # Use env variable or default
print(f"Using database URL: {DB_URL}")  # Debugging line to check the DB_URL
class WebServer:
    def __init__(self):
        self.database = database
        self.app = FastAPI(lifespan=self.lifespan)
        self.setup_routes()

    def setup_routes(self):
        @self.app.api_route('/', methods=['GET','HEAD'])
        def index():
            return "Bot is running!"

    @asynccontextmanager
    async def lifespan(self, app):
        print("Attempting to connect to the PostgreSQL server...")
        await self.database.connect()
        print("Connected to the PostgreSQL server.")
        try:
            yield
        finally:
            print("Disconnecting from the PostgreSQL server...")
            await self.database.disconnect()
            print("Disconnected from the PostgreSQL server.")

    def run(self):
        uvicorn.run(self.app, host='0.0.0.0', port=8080)

# Create a single instance for import/use elsewhere
webserver = WebServer()
run_web = webserver.run
app = webserver.app