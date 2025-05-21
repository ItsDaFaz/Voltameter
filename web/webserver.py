from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def index():
        return "Bot is running!"

    return app


def run_web():
    app = create_app()
    app.run(host='0.0.0.0', port=8080)
