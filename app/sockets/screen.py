import base64

from flask_socketio import emit

from app import socketio
from app.auth import socket_login_required
from app.services.capture import ScreenCapture

capture = ScreenCapture()
_streaming_clients = set()


@socketio.on("start_stream")
@socket_login_required
def handle_start_stream(data=None):
    from flask import request
    sid = request.sid
    _streaming_clients.add(sid)

    fps = 10
    quality = 50
    if data:
        fps = max(1, min(30, int(data.get("fps", 10))))
        quality = max(10, min(100, int(data.get("quality", 50))))

    emit("stream_started", {"status": "ok"})

    # Start streaming in a background loop for this client
    def stream_loop():
        interval = 1.0 / fps
        while sid in _streaming_clients:
            try:
                frame_bytes, size = capture.grab_frame(quality=quality)
                frame_b64 = base64.b64encode(frame_bytes).decode("ascii")
                socketio.emit("frame", {
                    "data": frame_b64,
                    "width": size.width,
                    "height": size.height,
                }, to=sid)
                socketio.sleep(interval)
            except Exception:
                socketio.sleep(0.5)

    socketio.start_background_task(stream_loop)


@socketio.on("update_stream")
@socket_login_required
def handle_update_stream(data):
    # Client can update FPS/quality - handled by restarting the stream
    from flask import request
    sid = request.sid
    _streaming_clients.discard(sid)
    socketio.sleep(0.2)  # Let old loop exit
    handle_start_stream(data)


@socketio.on("stop_stream")
@socket_login_required
def handle_stop_stream():
    from flask import request
    _streaming_clients.discard(request.sid)


def cleanup_screen(sid):
    """Called on disconnect to stop streaming for a client."""
    _streaming_clients.discard(sid)
