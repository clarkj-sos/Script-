"""Faceless YouTube Automation System — end-to-end pipeline."""
from __future__ import annotations
import importlib
from typing import TYPE_CHECKING

__version__ = "1.0.0"

# Map public names → (module, attribute) for lazy import.
# This keeps optional-dep modules (uploader needs google-*, tts_engine needs
# elevenlabs/edge-tts, video_assembler needs ffmpeg) from crashing the package
# when a consumer only wants a subset (e.g. just ThumbnailGenerator).
_LAZY = {
    "PipelineConfig":    ("faceless_youtube.config",             "PipelineConfig"),
    "ScriptGenerator":   ("faceless_youtube.script_generator",   "ScriptGenerator"),
    "VideoScript":       ("faceless_youtube.script_generator",   "VideoScript"),
    "ScriptSection":     ("faceless_youtube.script_generator",   "ScriptSection"),
    "ThumbnailGenerator":("faceless_youtube.thumbnail_generator","ThumbnailGenerator"),
    "ThumbnailPreset":   ("faceless_youtube.thumbnail_generator","ThumbnailPreset"),
    "FalImageClient":    ("faceless_youtube.fal_image_client",   "FalImageClient"),
    "TTSEngine":         ("faceless_youtube.tts_engine",         "TTSEngine"),
    "VideoAssembler":    ("faceless_youtube.video_assembler",    "VideoAssembler"),
    "VisualAsset":       ("faceless_youtube.video_assembler",    "VisualAsset"),
    "SubtitleEntry":     ("faceless_youtube.video_assembler",    "SubtitleEntry"),
    "SEOOptimizer":      ("faceless_youtube.seo_optimizer",      "SEOOptimizer"),
    "YouTubeUploader":   ("faceless_youtube.uploader",           "YouTubeUploader"),
    "ContentScheduler":  ("faceless_youtube.scheduler",          "ContentScheduler"),
    "ScheduledVideo":    ("faceless_youtube.scheduler",          "ScheduledVideo"),
    "AnalyticsTracker":  ("faceless_youtube.analytics",          "AnalyticsTracker"),
    "NicheLibrary":      ("faceless_youtube.niche_library",      "NicheLibrary"),
    "Pipeline":          ("faceless_youtube.pipeline",           "Pipeline"),
}

__all__ = list(_LAZY.keys())


def __getattr__(name: str):
    if name in _LAZY:
        module_name, attr = _LAZY[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value  # cache
        return value
    raise AttributeError(f"module 'faceless_youtube' has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)


if TYPE_CHECKING:
    from faceless_youtube.config import PipelineConfig
    from faceless_youtube.script_generator import ScriptGenerator, VideoScript, ScriptSection
    from faceless_youtube.thumbnail_generator import ThumbnailGenerator, ThumbnailPreset
    from faceless_youtube.fal_image_client import FalImageClient
    from faceless_youtube.tts_engine import TTSEngine
    from faceless_youtube.video_assembler import VideoAssembler, VisualAsset, SubtitleEntry
    from faceless_youtube.seo_optimizer import SEOOptimizer
    from faceless_youtube.uploader import YouTubeUploader
    from faceless_youtube.scheduler import ContentScheduler, ScheduledVideo
    from faceless_youtube.analytics import AnalyticsTracker
    from faceless_youtube.niche_library import NicheLibrary
    from faceless_youtube.pipeline import Pipeline
