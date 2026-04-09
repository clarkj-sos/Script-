"""fal.ai image client wrapping the nano-banana-2 (Google Gemini) endpoint.

Used by ThumbnailGenerator for AI-generated backgrounds and (optionally) by
the pipeline for per-section scene images. Falls back cleanly when the
``fal_client`` library is missing or no API key is configured — callers
should treat a ``RuntimeError`` from ``generate()`` as "skip, use solid
background".
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

FAL_MODEL_NANO_BANANA_2 = "fal-ai/nano-banana-2"
DEFAULT_IMAGE_MODEL = FAL_MODEL_NANO_BANANA_2


class FalImageClient:
    """Thin wrapper around fal_client.subscribe for image generation.

    Parameters
    ----------
    config:
        Any object exposing ``fal_api_key`` (str) and optionally
        ``image_model`` (str, defaults to nano-banana-2) and
        ``output_dir`` (str, for downloaded images).
    """

    def __init__(self, config: Any) -> None:
        self.config = config
        self.api_key: Optional[str] = (
            getattr(config, "fal_api_key", None) or os.getenv("FAL_KEY")
        )
        self.model: str = getattr(config, "image_model", DEFAULT_IMAGE_MODEL)
        self.output_dir: str = getattr(config, "output_dir", "output")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _load_client(self):
        """Lazy-import fal_client so a missing dep doesn't break import-time."""
        try:
            import fal_client  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "fal_client not installed. Run: pip install fal-client"
            ) from exc
        if not self.api_key:
            raise RuntimeError(
                "fal_api_key missing. Set config.fal_api_key or the FAL_KEY env var."
            )
        # fal_client reads FAL_KEY from the environment
        os.environ["FAL_KEY"] = self.api_key
        return fal_client

    def generate(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        num_images: int = 1,
        image_size: str = "landscape_16_9",
        output_format: str = "jpeg",
    ) -> str:
        """Generate a single image from a text prompt and return its local path.

        Raises
        ------
        RuntimeError
            If fal_client is missing, the key is not configured, the
            request fails, or the response has no image URL.
        """
        fal_client = self._load_client()

        output_path = output_path or os.path.join(
            self.output_dir, f"fal_{uuid.uuid4().hex[:12]}.{output_format}"
        )

        arguments = {
            "prompt": prompt,
            "num_images": num_images,
            "image_size": image_size,
            "output_format": output_format,
        }

        logger.info("fal.ai generate: model=%s prompt=%r", self.model, prompt[:80])
        try:
            result = fal_client.subscribe(
                self.model,
                arguments=arguments,
                with_logs=False,
            )
        except Exception as exc:
            raise RuntimeError(f"fal.ai request failed: {exc}") from exc

        url = self._extract_image_url(result)
        if not url:
            raise RuntimeError(f"fal.ai response contained no image URL: {result!r}")

        self._download(url, output_path)
        logger.info("fal.ai image saved to %s", output_path)
        return output_path

    def generate_thumbnail_background(
        self,
        title: str,
        style_notes: str = "",
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a 16:9 cinematic background for a YouTube thumbnail.

        The prompt explicitly requests NO text and leaves empty negative space
        so the ThumbnailGenerator can overlay its own title text on top.
        """
        style_clause = f" {style_notes}." if style_notes else ""
        prompt = (
            f"Cinematic YouTube thumbnail background illustrating: {title}.{style_clause} "
            "Dramatic lighting, photorealistic, high detail, 16:9 widescreen composition. "
            "Leave the center-left area uncluttered for a title text overlay. "
            "Absolutely no text, no letters, no words, no watermarks in the image."
        )
        return self.generate(
            prompt=prompt,
            output_path=output_path,
            num_images=1,
            image_size="landscape_16_9",
            output_format="jpeg",
        )

    def generate_scene_image(
        self,
        description: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a per-section scene image for the slideshow.

        Used by the pipeline when building visual assets from a script.
        """
        prompt = (
            f"Cinematic documentary still: {description}. "
            "Photorealistic, dramatic lighting, high detail, 16:9 widescreen. "
            "No text, no letters, no words, no watermarks."
        )
        return self.generate(
            prompt=prompt,
            output_path=output_path,
            num_images=1,
            image_size="landscape_16_9",
            output_format="jpeg",
        )

    @staticmethod
    def _extract_image_url(result: Any) -> Optional[str]:
        """Pull the first image URL from a fal.ai response.

        nano-banana-2 returns ``{"images": [{"url": "...", ...}], ...}``
        but we also handle a few alternative shapes defensively.
        """
        if not isinstance(result, dict):
            return None
        images = result.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                return first.get("url") or first.get("image_url")
            if isinstance(first, str):
                return first
        # Some models return {"image": {"url": "..."}}
        image = result.get("image")
        if isinstance(image, dict):
            return image.get("url")
        return None

    @staticmethod
    def _download(url: str, output_path: str, timeout: float = 60.0) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            Path(output_path).write_bytes(response.content)
