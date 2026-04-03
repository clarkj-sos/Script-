from flask import session
from flask_socketio import emit

from app import socketio
from app.auth import socket_login_required
from app.services.command_service import PtySession

# Per-client PTY sessions
_sessions = {}


@socketio.on("term_open")
@socket_login_required
def handle_term_open(data=None):
    from flask import request
    sid = request.sid

    cols = 80
    rows = 24
    if data:
        cols = int(data.get("cols", 80))
        rows = int(data.get("rows", 24))

    pty_session = PtySession()
    pty_session.start(cols, rows)
    _sessions[sid] = pty_session

    emit("term_opened", {"status": "ok"})

    # Start reading output in background
    def read_loop():
        while sid in _sessions:
            output = pty_session.read(timeout=0.05)
            if output:
                socketio.emit("term_output", {"data": output.decode("utf-8", errors="replace")}, to=sid)
            else:
                socketio.sleep(0.05)
            if not pty_session.alive:
                socketio.emit("term_closed", {}, to=sid)
                break

    socketio.start_background_task(read_loop)


@socketio.on("term_input")
@socket_login_required
def handle_term_input(data):
    from flask import request
    sid = request.sid
    pty_session = _sessions.get(sid)
    if pty_session and pty_session.alive:
        pty_session.write(data.get("data", ""))


@socketio.on("term_resize")
@socket_login_required
def handle_term_resize(data):
    from flask import request
    sid = request.sid
    pty_session = _sessions.get(sid)
    if pty_session:
        pty_session.resize(int(data.get("cols", 80)), int(data.get("rows", 24)))


@socketio.on("term_close")
@socket_login_required
def handle_term_close():
    from flask import request
    sid = request.sid
    pty_session = _sessions.pop(sid, None)
    if pty_session:
        pty_session.close()


def cleanup_terminal(sid):
    """Called on disconnect to close PTY session for a client."""
    pty_session = _sessions.pop(sid, None)
    if pty_session:
        pty_session.close()
