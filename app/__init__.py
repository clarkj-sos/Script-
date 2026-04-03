from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()


def create_app():
    from config import Config

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

    socketio.init_app(app, async_mode="eventlet", cors_allowed_origins=[])

    # Register blueprints
    from app.routes.desktop import desktop_bp
    from app.routes.terminal import terminal_bp
    from app.routes.files import files_bp
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(desktop_bp)
    app.register_blueprint(terminal_bp)
    app.register_blueprint(files_bp)

    # Register socket handlers
    from app.sockets import screen, input_handler, command  # noqa: F401

    return app
