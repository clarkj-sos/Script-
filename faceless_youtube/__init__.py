"""Faceless YouTube Automation System — end-to-end pipeline."""
__version__ = "1.0.0"

from faceless_youtube.config import PipelineConfig
from faceless_youtube.script_generator import ScriptGenerator, VideoScript, ScriptSection
from faceless_youtube.thumbnail_generator import ThumbnailGenerator, ThumbnailPreset
from faceless_youtube.tts_engine import TTSEngine
from faceless_youtube.video_assembler import VideoAssembler, VisualAsset, SubtitleEntry
from faceless_youtube.seo_optimizer import SEOOptimizer
from faceless_youtube.uploader import YouTubeUploader
from faceless_youtube.scheduler import ContentScheduler, ScheduledVideo
from faceless_youtube.analytics import AnalyticsTracker
from faceless_youtube.niche_library import NicheLibrary
from faceless_youtube.pipeline import Pipeline

__all__ = [
    "PipelineConfig", "ScriptGenerator", "VideoScript", "ScriptSection",
    "ThumbnailGenerator", "ThumbnailPreset", "TTSEngine",
    "VideoAssembler", "VisualAsset", "SubtitleEntry",
    "SEOOptimizer", "YouTubeUploader", "ContentScheduler", "ScheduledVideo",
    "AnalyticsTracker", "NicheLibrary", "Pipeline",
]
