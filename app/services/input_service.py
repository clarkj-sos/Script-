import pyautogui

# Disable pyautogui fail-safe (moving to corner won't abort)
pyautogui.FAILSAFE = False
# Disable the pause between actions for responsiveness
pyautogui.PAUSE = 0

# Allowed key names for validation
ALLOWED_KEYS = set(pyautogui.KEYBOARD_KEYS)


def validate_coords(x, y):
    """Ensure coordinates are within screen bounds."""
    w, h = pyautogui.size()
    x = max(0, min(int(x), w - 1))
    y = max(0, min(int(y), h - 1))
    return x, y


def mouse_move(x, y):
    x, y = validate_coords(x, y)
    pyautogui.moveTo(x, y, _pause=False)


def mouse_click(x, y, button="left"):
    x, y = validate_coords(x, y)
    btn = button if button in ("left", "right", "middle") else "left"
    pyautogui.click(x, y, button=btn, _pause=False)


def mouse_double_click(x, y, button="left"):
    x, y = validate_coords(x, y)
    btn = button if button in ("left", "right", "middle") else "left"
    pyautogui.doubleClick(x, y, button=btn, _pause=False)


def mouse_down(x, y, button="left"):
    x, y = validate_coords(x, y)
    btn = button if button in ("left", "right", "middle") else "left"
    pyautogui.mouseDown(x, y, button=btn, _pause=False)


def mouse_up(x, y, button="left"):
    x, y = validate_coords(x, y)
    btn = button if button in ("left", "right", "middle") else "left"
    pyautogui.mouseUp(x, y, button=btn, _pause=False)


def mouse_scroll(x, y, delta):
    x, y = validate_coords(x, y)
    pyautogui.scroll(int(delta), x, y, _pause=False)


def key_down(key):
    if key in ALLOWED_KEYS:
        pyautogui.keyDown(key, _pause=False)


def key_up(key):
    if key in ALLOWED_KEYS:
        pyautogui.keyUp(key, _pause=False)


def key_press(key):
    if key in ALLOWED_KEYS:
        pyautogui.press(key, _pause=False)


def hotkey(*keys):
    valid = [k for k in keys if k in ALLOWED_KEYS]
    if valid:
        pyautogui.hotkey(*valid, _pause=False)
