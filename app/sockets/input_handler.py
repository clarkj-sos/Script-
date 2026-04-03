from app import socketio
from app.auth import socket_login_required
from app.services import input_service


@socketio.on("mouse_move")
@socket_login_required
def handle_mouse_move(data):
    input_service.mouse_move(data["x"], data["y"])


@socketio.on("mouse_click")
@socket_login_required
def handle_mouse_click(data):
    input_service.mouse_click(data["x"], data["y"], data.get("button", "left"))


@socketio.on("mouse_dblclick")
@socket_login_required
def handle_mouse_dblclick(data):
    input_service.mouse_double_click(data["x"], data["y"], data.get("button", "left"))


@socketio.on("mouse_down")
@socket_login_required
def handle_mouse_down(data):
    input_service.mouse_down(data["x"], data["y"], data.get("button", "left"))


@socketio.on("mouse_up")
@socket_login_required
def handle_mouse_up(data):
    input_service.mouse_up(data["x"], data["y"], data.get("button", "left"))


@socketio.on("mouse_scroll")
@socket_login_required
def handle_mouse_scroll(data):
    input_service.mouse_scroll(data["x"], data["y"], data.get("delta", 0))


@socketio.on("key_down")
@socket_login_required
def handle_key_down(data):
    input_service.key_down(data["key"])


@socketio.on("key_up")
@socket_login_required
def handle_key_up(data):
    input_service.key_up(data["key"])


@socketio.on("key_press")
@socket_login_required
def handle_key_press(data):
    input_service.key_press(data["key"])


@socketio.on("hotkey")
@socket_login_required
def handle_hotkey(data):
    input_service.hotkey(*data.get("keys", []))
