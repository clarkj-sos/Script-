import io

import mss
from PIL import Image


class ScreenCapture:
    """Captures the screen using mss and encodes as JPEG."""

    def __init__(self, quality=50, monitor=0):
        self.quality = quality
        self.monitor = monitor

    def grab_frame(self, quality=None):
        """Capture a single frame and return JPEG bytes."""
        q = quality or self.quality
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[self.monitor])
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=q)
            return buf.getvalue(), raw.size

    def get_screen_size(self):
        """Return (width, height) of the captured monitor."""
        with mss.mss() as sct:
            mon = sct.monitors[self.monitor]
            return mon["width"], mon["height"]
