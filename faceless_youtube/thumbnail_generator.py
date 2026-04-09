"""Thumbnail generator with 6 design presets from the Stride document."""
from __future__ import annotations
import logging
import os, uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

logger = logging.getLogger(__name__)


# Presets

@dataclass
class ThumbnailPreset:
    name: str
    colors: Dict[str, str]
    font_main: str
    font_accent: str
    text_position: str = "center"  # "center" | "bottom" | "top"
    style_notes: str = ""


PRESETS: List[ThumbnailPreset] = [
    ThumbnailPreset(
        name="BLACK_HOLE_WARNING",
        colors={"bg": "#000000", "accent": "#FF7A00", "secondary": "#4DA6FF", "text": "#FFFFFF"},
        font_main="Anton", font_accent="Montserrat",
        text_position="center", style_notes="High urgency, warning vibe",
    ),
    ThumbnailPreset(
        name="WHATS_INSIDE",
        colors={"bg": "#0A0F2C", "accent": "#00E5FF", "secondary": "#F2F2F2", "text": "#FFFFFF"},
        font_main="Bebas Neue", font_accent="Lato",
        text_position="center", style_notes="Mysterious, POV style",
    ),
    ThumbnailPreset(
        name="NO_ESCAPE",
        colors={"bg": "#000000", "accent": "#FF4D00", "secondary": "#3A0CA3", "text": "#FFFFFF"},
        font_main="Impact", font_accent="Oswald",
        text_position="center", style_notes="Aggressive, dramatic",
    ),
    ThumbnailPreset(
        name="THE_VOID",
        colors={"bg": "#000000", "accent": "#F2C94C", "secondary": "#1B1F3B", "text": "#FFFFFF"},
        font_main="League Gothic", font_accent="Roboto Condensed",
        text_position="bottom", style_notes="Minimalist, premium",
    ),
    ThumbnailPreset(
        name="COSMIC_MONSTER",
        colors={"bg": "#000000", "accent": "#A259FF", "secondary": "#FF6A00", "text": "#FFFFFF"},
        font_main="Barlow", font_accent="Poppins",
        text_position="center", style_notes="Dramatic, vibrant",
    ),
    ThumbnailPreset(
        name="GRAVITY_GONE_WILD",
        colors={"bg": "#001F3F", "accent": "#00FFFF", "secondary": "#FFFFFF", "text": "#FFFFFF"},
        font_main="Eurostile", font_accent="Inter",
        text_position="center", style_notes="Sci-fi, educational",
    ),
]


# Generator

class ThumbnailGenerator:
    """Generates 1280x720 YouTube thumbnails using PIL."""

    SYSTEM_FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\impact.ttf",
    ]

    def __init__(self, config) -> None:
        self.config = config
        self.width = getattr(config, "thumbnail_width", 1280)
        self.height = getattr(config, "thumbnail_height", 720)
        self.output_dir = getattr(config, "output_dir", "output")
        self.presets: List[ThumbnailPreset] = list(PRESETS)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    # Public API

    def list_presets(self) -> List[str]:
        return [p.name for p in self.presets]

    def add_custom_preset(self, preset: ThumbnailPreset) -> None:
        self.presets.append(preset)

    def generate(
        self,
        text: str,
        preset: Union[str, int] = 1,
        output_path: Optional[str] = None,
        background_image: Optional[str] = None,
    ) -> str:
        p = self._resolve_preset(preset)
        output_path = output_path or self._default_output(p.name)

        # If no explicit background was supplied and the config opts in to the
        # fal.ai image backend, try to generate one via nano-banana-2. Any
        # failure (missing lib, missing key, network error) falls back silently
        # to the solid-color preset background so thumbnails always render.
        if background_image is None and getattr(self.config, "image_backend", "none") == "fal":
            background_image = self._try_generate_ai_background(text, p)

        # Background
        if background_image and os.path.exists(background_image):
            img = Image.open(background_image).convert("RGB")
            img = self._fit_to_canvas(img, self.width, self.height)
        else:
            img = Image.new("RGB", (self.width, self.height), p.colors["bg"])

        # Effects: gradient + glow + vignette
        img = self._apply_gradient(img, p.colors)
        img = self._apply_glow(img, p.colors["accent"], intensity=0.4)
        img = self._apply_vignette(img, intensity=0.55)

        # Text
        draw = ImageDraw.Draw(img)
        self._render_main_text(draw, text, p)

        img.save(output_path, "JPEG", quality=92, optimize=True)
        return output_path

    def generate_all_presets(self, text: str, output_dir: Optional[str] = None) -> List[str]:
        out_dir = output_dir or self.output_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        results = []
        for i, p in enumerate(self.presets, 1):
            path = os.path.join(out_dir, f"thumb_{i:02d}_{p.name}.jpg")
            results.append(self.generate(text, preset=i, output_path=path))
        return results

    # Helpers

    def _try_generate_ai_background(self, text: str, preset: ThumbnailPreset) -> Optional[str]:
        """Generate an AI background via fal.ai, or return None on any failure."""
        try:
            from faceless_youtube.fal_image_client import FalImageClient
            client = FalImageClient(self.config)
            out_path = os.path.join(
                self.output_dir,
                f"thumb_bg_{preset.name}_{uuid.uuid4().hex[:8]}.jpeg",
            )
            return client.generate_thumbnail_background(
                title=text,
                style_notes=preset.style_notes,
                output_path=out_path,
            )
        except Exception as exc:
            logger.warning(
                "AI background generation failed (%s: %s), falling back to solid color.",
                type(exc).__name__, exc,
            )
            return None

    def _resolve_preset(self, preset: Union[str, int]) -> ThumbnailPreset:
        if isinstance(preset, int):
            if not (1 <= preset <= len(self.presets)):
                raise ValueError(f"preset index out of range: {preset}")
            return self.presets[preset - 1]
        for p in self.presets:
            if p.name.lower() == str(preset).lower():
                return p
        raise ValueError(f"Unknown preset: {preset}")

    def _default_output(self, name: str) -> str:
        return os.path.join(self.output_dir, f"thumb_{name}_{uuid.uuid4().hex[:8]}.jpg")

    @staticmethod
    def _fit_to_canvas(img: Image.Image, w: int, h: int) -> Image.Image:
        src_w, src_h = img.size
        scale = max(w / src_w, h / src_h)
        new_size = (int(src_w * scale), int(src_h * scale))
        img = img.resize(new_size, Image.LANCZOS)
        left = (img.width - w) // 2
        top = (img.height - h) // 2
        return img.crop((left, top, left + w, top + h))

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _apply_gradient(self, img: Image.Image, colors: Dict[str, str]) -> Image.Image:
        """Darken edges, brighten center for text legibility."""
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        cx, cy = img.width // 2, img.height // 2
        max_r = int((img.width ** 2 + img.height ** 2) ** 0.5 / 2)
        steps = 30
        for i in range(steps):
            r = int(max_r * (i / steps))
            alpha = int(140 * (i / steps))
            d.ellipse(
                [cx - max_r + r, cy - max_r + r, cx + max_r - r, cy + max_r - r],
                outline=(0, 0, 0, alpha),
            )
        overlay = overlay.filter(ImageFilter.GaussianBlur(40))
        return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    def _apply_glow(self, img: Image.Image, color: str, intensity: float = 0.4) -> Image.Image:
        glow = Image.new("RGB", img.size, self._hex_to_rgb(color))
        glow = glow.filter(ImageFilter.GaussianBlur(120))
        return Image.blend(img, glow, intensity * 0.25)

    def _apply_vignette(self, img: Image.Image, intensity: float = 0.5) -> Image.Image:
        mask = Image.new("L", img.size, 0)
        d = ImageDraw.Draw(mask)
        for i in range(60):
            alpha = int(255 * (1 - i / 60) * intensity)
            d.ellipse(
                [i * 8, i * 5, img.width - i * 8, img.height - i * 5],
                fill=255 - alpha,
            )
        mask = mask.filter(ImageFilter.GaussianBlur(80))
        black = Image.new("RGB", img.size, (0, 0, 0))
        return Image.composite(img, black, mask)

    def _get_font(self, font_name: str, size: int) -> ImageFont.ImageFont:
        # Try the explicit config path first
        explicit = getattr(self.config, "thumbnail_font_path", None)
        if explicit and os.path.exists(explicit):
            try:
                return ImageFont.truetype(explicit, size)
            except OSError:
                pass
        # Try system font paths
        for path in self.SYSTEM_FONT_PATHS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
        # Last resort
        return ImageFont.load_default()

    def _render_main_text(self, draw: ImageDraw.ImageDraw, text: str, preset: ThumbnailPreset) -> None:
        text = text.upper()
        # Auto-size based on text length and canvas width
        target_width = int(self.width * 0.85)
        font_size = 180
        while font_size > 40:
            font = self._get_font(preset.font_main, font_size)
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except AttributeError:
                tw, th = draw.textsize(text, font=font)
            if tw <= target_width:
                break
            font_size -= 10
        else:
            font = self._get_font(preset.font_main, 40)
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

        x = (self.width - tw) // 2
        if preset.text_position == "bottom":
            y = self.height - th - 80
        elif preset.text_position == "top":
            y = 60
        else:
            y = (self.height - th) // 2

        # Drop shadow
        shadow_color = (0, 0, 0)
        for dx, dy in [(4, 4), (3, 3), (2, 2)]:
            draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)

        # Outline (multi-pass for thick stroke)
        outline_color = self._hex_to_rgb(preset.colors["accent"])
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            for dy in (-3, -2, -1, 0, 1, 2, 3):
                if dx or dy:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

        # Main fill
        draw.text((x, y), text, font=font, fill=self._hex_to_rgb(preset.colors["text"]))
