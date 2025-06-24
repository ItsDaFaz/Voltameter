from fastapi import FastAPI, Request, HTTPException
import uvicorn
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from db.session import get_engine  # Import the engine factory
from bot import leaderboard_manager  # Import the leaderboard manager instance
import asyncio
from utils.helpers import bool_parse
load_dotenv(override=True)  # Load environment variables from .env file
CRON_SECRET = os.getenv("CRON_SECRET", "default_secret")  # Default secret if not set


class WebServer:
    def __init__(self):
        self.engine = get_engine()  # Create engine in this thread/event loop
        self.app = FastAPI(lifespan=self.lifespan)
        self.leaderboard_manager = None
        self.setup_routes()

    def set_leaderboard_manager(self, manager):
        
        self.leaderboard_manager = manager
        print("Leaderboard manager set in webserver.")

    def setup_routes(self):
        @self.app.api_route('/', methods=['GET','HEAD'])
        def index():
            return "Bot is running!"

        @self.app.post('/trigger-auto-winner')
        async def trigger_auto_winner(request: Request):
            if self.leaderboard_manager is None:
                raise HTTPException(status_code=500, detail="Leaderboard manager not set")
            try:
                auth = request.headers.get("Authorization")
                data = await request.json()
                is_test: bool = bool_parse(data.get("test", False))

                if auth != f"Bearer {CRON_SECRET}":
                    raise HTTPException(status_code=401, detail="Unauthorized")
                try:
                    await self.leaderboard_manager.auto_winner(test=is_test)
                    return {"status": "success", "message": "auto_winner executed"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Bad request: {str(e)}")

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