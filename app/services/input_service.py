"""Input service for mouse/keyboard control.

Uses pynput when an X display is available, falls back to xdotool via subprocess.
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

_backend = None  # "pynput", "xdotool", or None


def _init_backend():
    global _backend
    if _backend is not None:
        return

    # Try pynput first
    try:
        from pynput.mouse import Controller as MouseController
        from pynput.keyboard import Controller as KeyboardController
        # Test that it can actually connect
        MouseController()
        _backend = "pynput"
        logger.info("Input backend: pynput")
        return
    except Exception:
        pass

    # Try xdotool
    try:
        subprocess.run(["xdotool", "--version"], capture_output=True, check=True)
        _backend = "xdotool"
        logger.info("Input backend: xdotool")
        return
    except Exception:
        pass

    _backend = "none"
    logger.warning("No input backend available. Mouse/keyboard control disabled.")


# --- pynput helpers (lazy-loaded) ---

_mouse = None
_keyboard = None


def _get_pynput():
    global _mouse, _keyboard
    if _mouse is None:
        from pynput.mouse import Controller as MouseController
        from pynput.keyboard import Controller as KeyboardController
        _mouse = MouseController()
        _keyboard = KeyboardController()
    return _mouse, _keyboard


def _pynput_key(key_name):
    from pynput.keyboard import Key
    KEY_MAP = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift, "alt": Key.alt, "meta": Key.cmd, "win": Key.cmd,
        "enter": Key.enter, "backspace": Key.backspace, "tab": Key.tab,
        "escape": Key.esc, "delete": Key.delete, "insert": Key.insert,
        "home": Key.home, "end": Key.end, "pageup": Key.page_up, "pagedown": Key.page_down,
        "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
        "capslock": Key.caps_lock, "space": Key.space,
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    }
    lower = key_name.lower()
    if lower in KEY_MAP:
        return KEY_MAP[lower]
    if len(key_name) == 1:
        return key_name
    return None


def _pynput_button(button_name):
    from pynput.mouse import Button
    return {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(button_name, Button.left)


# --- xdotool helpers ---

def _xdo(*args):
    try:
        subprocess.run(["xdotool"] + list(args), capture_output=True, timeout=2)
    except Exception:
        pass


_XDOTOOL_KEY_MAP = {
    "ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt",
    "meta": "super", "win": "super", "enter": "Return", "backspace": "BackSpace",
    "tab": "Tab", "escape": "Escape", "delete": "Delete", "insert": "Insert",
    "home": "Home", "end": "End", "pageup": "Prior", "pagedown": "Next",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "capslock": "Caps_Lock", "space": "space",
}


def _xdo_key(key_name):
    lower = key_name.lower()
    if lower in _XDOTOOL_KEY_MAP:
        return _XDOTOOL_KEY_MAP[lower]
    if lower.startswith("f") and lower[1:].isdigit():
        return key_name.upper()
    if len(key_name) == 1:
        return key_name
    return key_name


def _xdo_button(button_name):
    return {"left": "1", "middle": "2", "right": "3"}.get(button_name, "1")


# --- Public API ---

def mouse_move(x, y):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))


def mouse_click(x, y, button="left"):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
        m.click(_pynput_button(button))
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))
        _xdo("click", _xdo_button(button))


def mouse_double_click(x, y, button="left"):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
        m.click(_pynput_button(button), 2)
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))
        _xdo("click", "--repeat", "2", _xdo_button(button))


def mouse_down(x, y, button="left"):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
        m.press(_pynput_button(button))
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))
        _xdo("mousedown", _xdo_button(button))


def mouse_up(x, y, button="left"):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
        m.release(_pynput_button(button))
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))
        _xdo("mouseup", _xdo_button(button))


def mouse_scroll(x, y, delta):
    _init_backend()
    if _backend == "pynput":
        m, _ = _get_pynput()
        m.position = (int(x), int(y))
        m.scroll(0, int(delta))
    elif _backend == "xdotool":
        _xdo("mousemove", str(int(x)), str(int(y)))
        btn = "4" if int(delta) > 0 else "5"
        for _ in range(abs(int(delta))):
            _xdo("click", btn)


def key_down(key):
    _init_backend()
    if _backend == "pynput":
        _, kb = _get_pynput()
        resolved = _pynput_key(key)
        if resolved is not None:
            kb.press(resolved)
    elif _backend == "xdotool":
        _xdo("keydown", _xdo_key(key))


def key_up(key):
    _init_backend()
    if _backend == "pynput":
        _, kb = _get_pynput()
        resolved = _pynput_key(key)
        if resolved is not None:
            kb.release(resolved)
    elif _backend == "xdotool":
        _xdo("keyup", _xdo_key(key))


def key_press(key):
    _init_backend()
    if _backend == "pynput":
        _, kb = _get_pynput()
        resolved = _pynput_key(key)
        if resolved is not None:
            kb.press(resolved)
            kb.release(resolved)
    elif _backend == "xdotool":
        _xdo("key", _xdo_key(key))


def hotkey(*keys):
    _init_backend()
    if _backend == "pynput":
        _, kb = _get_pynput()
        resolved = [_pynput_key(k) for k in keys]
        resolved = [k for k in resolved if k is not None]
        for k in resolved:
            kb.press(k)
        for k in reversed(resolved):
            kb.release(k)
    elif _backend == "xdotool":
        combo = "+".join(_xdo_key(k) for k in keys)
        _xdo("key", combo)
