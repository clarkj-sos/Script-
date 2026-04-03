from app import socketio


@socketio.on("disconnect")
def handle_disconnect():
    from flask import request
    sid = request.sid

    from app.sockets.screen import cleanup_screen
    from app.sockets.command import cleanup_terminal

    cleanup_screen(sid)
    cleanup_terminal(sid)
