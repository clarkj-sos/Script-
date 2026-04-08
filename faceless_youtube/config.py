"""Pipeline configuration for the Faceless YouTube Automation System."""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class PipelineConfig:
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # TTS backend selection: "elevenlabs" | "edge-tts" | "gtts"
    tts_backend: str = "edge-tts"

    # YouTube
    youtube_api_key: Optional[str] = None
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_refresh_token: Optional[str] = None

    # Directories
    output_dir: str = "output"
    temp_dir: str = "temp"

    # Video
    video_width: int = 1920
    video_height: int = 1080
    video_fps: int = 30
    video_format: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"

    # For VideoAssembler compatibility
    @property
    def resolution_width(self) -> int: return self.video_width
    @property
    def resolution_height(self) -> int: return self.video_height
    @property
    def fps(self) -> int: return self.video_fps

    # Thumbnail
    thumbnail_width: int = 1280
    thumbnail_height: int = 720
    thumbnail_format: str = "jpg"
    thumbnail_font_path: Optional[str] = None

    # Content/niche
    default_niche: str = "space_science"
    niche: str = "space_science"  # alias used by some modules
    default_topic: Optional[str] = None
    min_script_words: int = 800
    max_script_words: int = 2000
    target_video_length_minutes: float = 10.0
    target_video_length_min_minutes: int = 8
    target_video_length_max_minutes: int = 15

    # Upload
    privacy_status: str = "private"
    notify_subscribers: bool = True
    made_for_kids: bool = False
    video_category_id: str = "22"
    default_tags: List[str] = field(default_factory=lambda: ["education", "documentary"])

    # Scheduler
    videos_per_week: int = 3
    upload_days: List[str] = field(default_factory=lambda: ["Monday", "Wednesday", "Friday"])
    upload_time: str = "15:00"
    upload_timezone: str = "America/New_York"

    # Analytics
    analytics_lookback_days: int = 28
    analytics_report_dir: str = "reports"

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        def _b(v): return str(v).lower() in ("true", "1", "yes")
        def _l(v, d):
            try:
                p = json.loads(v); return p if isinstance(p, list) else d
            except Exception: return d
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            tts_backend=os.getenv("TTS_BACKEND", "edge-tts"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
            youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID"),
            youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
            youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            temp_dir=os.getenv("TEMP_DIR", "temp"),
            default_niche=os.getenv("DEFAULT_NICHE", "space_science"),
            niche=os.getenv("DEFAULT_NICHE", "space_science"),
            privacy_status=os.getenv("PRIVACY_STATUS", "private"),
            notify_subscribers=_b(os.getenv("NOTIFY_SUBSCRIBERS", "true")),
            videos_per_week=int(os.getenv("VIDEOS_PER_WEEK", "3")),
            upload_days=_l(os.getenv("UPLOAD_DAYS", '["Monday","Wednesday","Friday"]'),
                           ["Monday", "Wednesday", "Friday"]),
            upload_time=os.getenv("UPLOAD_TIME", "15:00"),
        )

    @classmethod
    def from_file(cls, path) -> "PipelineConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = cls.from_env()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def save(self, path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def validate(self) -> None:
        errors = []
        if not self.openai_api_key:
            errors.append("openai_api_key is missing (set OPENAI_API_KEY)")
        if self.tts_backend == "elevenlabs" and not self.elevenlabs_api_key:
            errors.append("elevenlabs_api_key required when tts_backend=elevenlabs")
        if not (self.youtube_client_id and self.youtube_client_secret and self.youtube_refresh_token):
            errors.append("YouTube OAuth credentials incomplete (uploads will fail)")
        if self.privacy_status not in {"public", "private", "unlisted"}:
            errors.append(f"privacy_status invalid: {self.privacy_status}")
        if errors:
            raise ValueError("Config validation failed:\n  - " + "\n  - ".join(errors))

    def ensure_directories(self) -> None:
        for d in (self.output_dir, self.temp_dir, self.analytics_report_dir):
            Path(d).mkdir(parents=True, exist_ok=True)
