"""
faceless_youtube/tts_engine.py

Text-to-speech engine for faceless YouTube automation.
Supports ElevenLabs (premium), Edge-TTS (free, Microsoft), and gTTS (free, Google).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Constants

ELEVENLABS_API_BASE = "https://api.elevenlabs.io"
ELEVENLABS_MAX_CHARS = 5_000          # per-request character limit
EDGE_TTS_DEFAULT_VOICE = "en-US-GuyNeural"
WORDS_PER_MINUTE = 150                # conservative narration pace
PAUSE_BETWEEN_SECTIONS_MS = 750       # silence gap between script sections

# Mapping of friendly backend names to canonical keys
BACKEND_ALIASES: dict[str, str] = {
    "elevenlabs": "elevenlabs",
    "eleven_labs": "elevenlabs",
    "eleven-labs": "elevenlabs",
    "edge-tts": "edge-tts",
    "edge_tts": "edge-tts",
    "edgetts": "edge-tts",
    "gtts": "gtts",
    "google": "gtts",
}

SUPPORTED_BACKENDS = {"elevenlabs", "edge-tts", "gtts"}


@dataclass
class PipelineConfig:
    """Minimal config expected by TTSEngine (subset of full PipelineConfig)."""

    output_dir: str = "output"
    temp_dir: str = "temp"
    tts_backend: str = "edge-tts"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity_boost: float = 0.75
    elevenlabs_style: float = 0.0
    edge_tts_voice: str = EDGE_TTS_DEFAULT_VOICE
    gtts_lang: str = "en"
    gtts_tld: str = "com"
    background_music_volume: float = 0.15
    extra: dict[str, Any] = field(default_factory=dict)


# Utility helpers

def _clean_text(text: str) -> str:
    """Remove markdown formatting and problematic characters before synthesis."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_]{1,3}(.*?)[*_]{1,3}", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_text(text: str, max_chars: int = ELEVENLABS_MAX_CHARS) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _tmp_path(temp_dir: str, suffix: str = ".mp3") -> str:
    _ensure_dir(temp_dir)
    fd, path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
    os.close(fd)
    return path


class TTSEngine:
    """
    Unified text-to-speech engine with multiple backend support.

    Backends:
    - elevenlabs : ElevenLabs REST API v1 (requires API key)
    - edge-tts   : Microsoft Edge TTS (free)
    - gtts       : Google Text-to-Speech (free)
    """

    def __init__(self, config) -> None:
        self.config = config
        self._backend = self._resolve_backend(config.tts_backend)

        _ensure_dir(config.output_dir)
        _ensure_dir(config.temp_dir)

        logger.info("TTSEngine initialised with backend=%s", self._backend)

    # Public API

    def synthesize(
        self,
        text: str,
        output_path: str | None = None,
        voice: str | None = None,
    ) -> str:
        if not text or not text.strip():
            raise ValueError("synthesize() received empty text")

        text = _clean_text(text)
        if output_path is None:
            output_path = os.path.join(
                self.config.output_dir,
                f"tts_{int(time.time() * 1000)}.mp3",
            )

        logger.debug("Synthesizing %d chars with backend=%s", len(text), self._backend)

        if self._backend == "elevenlabs":
            self._synthesize_elevenlabs(text, output_path, voice)
        elif self._backend == "edge-tts":
            self._synthesize_edge_tts(text, output_path, voice)
        elif self._backend == "gtts":
            self._synthesize_gtts(text, output_path, voice)
        else:
            raise RuntimeError(f"Unknown backend: {self._backend!r}")

        logger.info("Audio written to %s", output_path)
        return os.path.abspath(output_path)

    def synthesize_script(
        self,
        script_sections: list[dict],
        output_path: str | None = None,
    ) -> str:
        if not script_sections:
            raise ValueError("script_sections must not be empty")

        if output_path is None:
            output_path = os.path.join(
                self.config.output_dir,
                f"script_{int(time.time() * 1000)}.mp3",
            )

        section_files: list[str] = []

        for idx, section in enumerate(script_sections):
            text = section.get("text", "")
            if not text or not text.strip():
                logger.debug("Skipping empty section %d", idx)
                continue

            voice = section.get("voice")
            pause_ms = int(section.get("pause_after_ms", PAUSE_BETWEEN_SECTIONS_MS))

            section_path = _tmp_path(self.config.temp_dir, suffix=".mp3")
            self.synthesize(text, output_path=section_path, voice=voice)
            section_files.append(section_path)

            if pause_ms > 0 and idx < len(script_sections) - 1:
                silence_path = self._add_pause(pause_ms)
                section_files.append(silence_path)

        if not section_files:
            raise RuntimeError("No audio was produced from script_sections")

        result = self._concatenate_audio(section_files, output_path)

        for f in section_files:
            try:
                os.unlink(f)
            except OSError:
                pass

        logger.info("Script audio written to %s", result)
        return result

    def list_voices(self, backend: str | None = None) -> list[dict]:
        target = self._resolve_backend(backend) if backend else self._backend

        if target == "elevenlabs":
            return self._list_voices_elevenlabs()
        elif target == "edge-tts":
            return self._list_voices_edge_tts()
        elif target == "gtts":
            return self._list_voices_gtts()
        else:
            raise ValueError(f"Unknown backend: {target!r}")

    def set_backend(self, backend: str) -> None:
        resolved = self._resolve_backend(backend)
        logger.info("Switching TTS backend: %s -> %s", self._backend, resolved)
        self._backend = resolved
        self.config.tts_backend = resolved

    def estimate_duration(self, text: str) -> float:
        clean = _clean_text(text)
        word_count = len(clean.split())
        return (word_count / WORDS_PER_MINUTE) * 60.0

    # Backend: ElevenLabs

    def _synthesize_elevenlabs(self, text: str, output_path: str, voice: str | None) -> None:
        api_key = self.config.elevenlabs_api_key
        if not api_key:
            raise EnvironmentError("elevenlabs_api_key is not set in PipelineConfig")

        voice_id = voice or self.config.elevenlabs_voice_id
        chunks = _chunk_text(text)

        if len(chunks) == 1:
            self._elevenlabs_request(chunks[0], output_path, voice_id)
        else:
            chunk_files: list[str] = []
            for chunk in chunks:
                chunk_path = _tmp_path(self.config.temp_dir, suffix=".mp3")
                self._elevenlabs_request(chunk, chunk_path, voice_id)
                chunk_files.append(chunk_path)
            self._concatenate_audio(chunk_files, output_path)
            for f in chunk_files:
                try:
                    os.unlink(f)
                except OSError:
                    pass

    def _elevenlabs_request(
        self, text: str, output_path: str, voice_id: str,
        *, retries: int = 3, backoff: float = 2.0,
    ) -> None:
        url = f"{ELEVENLABS_API_BASE}/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.config.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": getattr(self.config, "elevenlabs_stability", 0.5),
                "similarity_boost": getattr(self.config, "elevenlabs_similarity_boost", 0.75),
                "style": getattr(self.config, "elevenlabs_style", 0.0),
                "use_speaker_boost": True,
            },
        }

        for attempt in range(1, retries + 1):
            try:
                with httpx.stream("POST", url, headers=headers, json=payload, timeout=120.0) as response:
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", backoff * attempt))
                        logger.warning("ElevenLabs rate-limited. Waiting %.1fs (attempt %d/%d)",
                                       retry_after, attempt, retries)
                        time.sleep(retry_after)
                        continue

                    response.raise_for_status()

                    _ensure_dir(os.path.dirname(output_path) or ".")
                    with open(output_path, "wb") as fh:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            fh.write(chunk)
                    return

            except httpx.HTTPStatusError as exc:
                logger.error("ElevenLabs HTTP error %s on attempt %d/%d: %s",
                             exc.response.status_code, attempt, retries, exc)
                if attempt == retries:
                    raise
                time.sleep(backoff * attempt)

            except httpx.RequestError as exc:
                logger.error("ElevenLabs request error on attempt %d/%d: %s", attempt, retries, exc)
                if attempt == retries:
                    raise
                time.sleep(backoff * attempt)

        raise RuntimeError(f"ElevenLabs synthesis failed after {retries} attempts")

    def _list_voices_elevenlabs(self) -> list[dict]:
        api_key = self.config.elevenlabs_api_key
        if not api_key:
            raise EnvironmentError("elevenlabs_api_key is not set")

        resp = httpx.get(
            f"{ELEVENLABS_API_BASE}/v1/voices",
            headers={"xi-api-key": api_key},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        voices = []
        for v in data.get("voices", []):
            voices.append({
                "voice_id": v.get("voice_id", ""),
                "name": v.get("name", ""),
                "category": v.get("category", ""),
                "description": v.get("description", ""),
                "backend": "elevenlabs",
            })
        return voices

    # Backend: Edge-TTS

    def _synthesize_edge_tts(self, text: str, output_path: str, voice: str | None) -> None:
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError("edge_tts package is not installed. Run: pip install edge-tts") from exc

        voice_name = voice or getattr(self.config, "edge_tts_voice", EDGE_TTS_DEFAULT_VOICE)
        _ensure_dir(os.path.dirname(output_path) or ".")

        asyncio.run(self._edge_tts_communicate(text, output_path, voice_name, edge_tts))

    @staticmethod
    async def _edge_tts_communicate(text: str, output_path: str, voice: str, edge_tts: Any) -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def _list_voices_edge_tts(self) -> list[dict]:
        try:
            import edge_tts
        except ImportError as exc:
            raise ImportError("edge_tts package is not installed. Run: pip install edge-tts") from exc

        async def _fetch() -> list[dict]:
            voices_raw = await edge_tts.list_voices()
            result = []
            for v in voices_raw:
                result.append({
                    "voice_id": v.get("ShortName", ""),
                    "name": v.get("FriendlyName", v.get("ShortName", "")),
                    "locale": v.get("Locale", ""),
                    "gender": v.get("Gender", ""),
                    "backend": "edge-tts",
                })
            return result

        return asyncio.run(_fetch())

    # Backend: gTTS

    def _synthesize_gtts(self, text: str, output_path: str, voice: str | None) -> None:
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise ImportError("gtts package is not installed. Run: pip install gTTS") from exc

        if voice:
            logger.warning("gTTS backend does not support custom voices; ignoring voice=%r.", voice)

        lang = getattr(self.config, "gtts_lang", "en")
        tld = getattr(self.config, "gtts_tld", "com")

        chunks = _chunk_text(text, max_chars=5_000)

        if len(chunks) == 1:
            tts = gTTS(text=chunks[0], lang=lang, tld=tld, slow=False)
            _ensure_dir(os.path.dirname(output_path) or ".")
            tts.save(output_path)
        else:
            chunk_files: list[str] = []
            for chunk in chunks:
                chunk_path = _tmp_path(self.config.temp_dir, suffix=".mp3")
                tts = gTTS(text=chunk, lang=lang, tld=tld, slow=False)
                tts.save(chunk_path)
                chunk_files.append(chunk_path)
            self._concatenate_audio(chunk_files, output_path)
            for f in chunk_files:
                try:
                    os.unlink(f)
                except OSError:
                    pass

    def _list_voices_gtts(self) -> list[dict]:
        try:
            from gtts.lang import tts_langs
        except ImportError as exc:
            raise ImportError("gtts package is not installed. Run: pip install gTTS") from exc

        return [
            {"voice_id": lang_code, "name": lang_name, "locale": lang_code, "backend": "gtts"}
            for lang_code, lang_name in tts_langs().items()
        ]

    # Audio processing helpers

    def _add_pause(self, duration_ms: int) -> str:
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise ImportError("pydub package is not installed. Run: pip install pydub") from exc

        silence = AudioSegment.silent(duration=duration_ms)
        path = _tmp_path(self.config.temp_dir, suffix=".mp3")
        silence.export(path, format="mp3")
        return path

    def _concatenate_audio(self, files: list[str], output_path: str) -> str:
        if not files:
            raise ValueError("_concatenate_audio received an empty file list")

        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise ImportError("pydub package is not installed. Run: pip install pydub") from exc

        combined = AudioSegment.empty()
        for fp in files:
            try:
                segment = AudioSegment.from_file(fp)
                combined += segment
            except Exception as exc:
                logger.warning("Could not load audio file %s: %s", fp, exc)

        _ensure_dir(os.path.dirname(output_path) or ".")
        combined.export(output_path, format="mp3", bitrate="192k")
        return os.path.abspath(output_path)

    def _normalize_audio(self, path: str) -> str:
        try:
            from pydub import AudioSegment, effects
        except ImportError as exc:
            raise ImportError("pydub package is not installed. Run: pip install pydub") from exc

        audio = AudioSegment.from_file(path)
        normalised = effects.normalize(audio)
        normalised.export(path, format="mp3", bitrate="192k")
        logger.debug("Normalised audio: %s", path)
        return os.path.abspath(path)

    def _add_background_music(
        self, voice_path: str, music_path: str, music_volume: float | None = None,
    ) -> str:
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise ImportError("pydub package is not installed. Run: pip install pydub") from exc

        vol = music_volume if music_volume is not None else getattr(self.config, "background_music_volume", 0.15)

        voice = AudioSegment.from_file(voice_path)
        music = AudioSegment.from_file(music_path)

        if len(music) < len(voice):
            repeats = (len(voice) // len(music)) + 1
            music = music * repeats

        music = music[: len(voice)]

        import math
        db_reduction = 20 * math.log10(max(vol, 1e-9))
        music = music + db_reduction

        mixed = voice.overlay(music)
        mixed.export(voice_path, format="mp3", bitrate="192k")
        logger.debug("Background music mixed into %s at volume=%.2f", voice_path, vol)
        return os.path.abspath(voice_path)

    @staticmethod
    def _resolve_backend(name: str) -> str:
        key = BACKEND_ALIASES.get(name.lower().strip())
        if key is None:
            raise ValueError(f"Unknown TTS backend {name!r}. Supported: {sorted(SUPPORTED_BACKENDS)}")
        return key
