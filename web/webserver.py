from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from db.session import get_engine  # Import the engine factory

load_dotenv(override=True)  # Load environment variables from .env file

class WebServer:
    def __init__(self):
        self.engine = get_engine()  # Create engine in this thread/event loop
        self.app = FastAPI(lifespan=self.lifespan)
        self.setup_routes()

    def setup_routes(self):
        @self.app.api_route('/', methods=['GET','HEAD'])
        def index():
            return "Bot is running!"

    @asynccontextmanager
    async def lifespan(self, app):
        print("Attempting to connect to the database engine...")
        try:
            # Try to actually connect to the database to verify connection
            async with self.engine.connect() as conn:
                print("Successfully connected to the database!")
            yield
        except Exception as e:
            print(f"Failed to connect to the database: {e}")
            raise
        finally:
            print("Lifespan shutdown. No explicit disconnect needed for SQLAlchemy engine.")

    def run(self):
        uvicorn.run(self.app, host='0.0.0.0', port=8080)

# Create a single instance for import/use elsewhere
webserver = WebServer()
run_web = webserver.run
app = webserver.app