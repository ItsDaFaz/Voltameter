from fastapi import FastAPI
import uvicorn

class WebServer:
    def __init__(self):
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self):
        @self.app.api_route('/', methods=['GET','HEAD'])
        def index():
            return "Bot is running!"

    def run(self):
        uvicorn.run(self.app, host='0.0.0.0', port=8080)

# Create a single instance for import/use elsewhere
webserver = WebServer()
run_web = webserver.run
app = webserver.app