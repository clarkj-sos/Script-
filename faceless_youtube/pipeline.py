"""
faceless_youtube/pipeline.py

Main Pipeline orchestrator that ties together all components of the
faceless YouTube automation system.
"""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """
    Central configuration object for the entire pipeline.

    All paths are resolved relative to `base_dir` when they are relative.
    """

    # ---- Directories -------------------------------------------------------
    base_dir: str = "output"
    scripts_dir: str = "output/scripts"
    audio_dir: str = "output/audio"
    thumbnails_dir: str = "output/thumbnails"
    videos_dir: str = "output/videos"
    assets_dir: str = "assets"
    logs_dir: str = "logs"

    # ---- OpenAI / LLM ------------------------------------------------------
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    script_max_tokens: int = 2000
    script_temperature: float = 0.7

    # ---- TTS ---------------------------------------------------------------
    tts_provider: str = "openai"          # "openai" | "gtts" | "elevenlabs"
    tts_voice: str = "alloy"
    tts_model: str = "tts-1"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # ---- Video -------------------------------------------------------------
    video_resolution: tuple = (1920, 1080)
    video_fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    placeholder_color: tuple = (15, 15, 30)   # dark navy default
    subtitle_font_size: int = 48
    subtitle_color: str = "white"
    subtitle_outline_color: str = "black"

    # ---- Thumbnail ---------------------------------------------------------
    thumbnail_width: int = 1280
    thumbnail_height: int = 720
    thumbnail_font: str = ""              # path to TTF; empty = PIL default
    thumbnail_presets: dict = field(default_factory=dict)

    # ---- SEO ---------------------------------------------------------------
    default_niche: str = "general"
    max_tags: int = 15
    description_max_chars: int = 5000

    # ---- YouTube API -------------------------------------------------------
    youtube_client_secrets_file: str = "client_secrets.json"
    youtube_token_file: str = "token.json"
    youtube_category_id: str = "28"       # Science & Technology
    youtube_privacy: str = "public"       # "public" | "unlisted" | "private"
    youtube_made_for_kids: bool = False

    # ---- Scheduling --------------------------------------------------------
    schedule_file: str = "output/schedule.json"
    default_upload_times: list = field(
        default_factory=lambda: ["09:00", "15:00", "20:00"]
    )
    timezone: str = "UTC"

    # ---- Analytics ---------------------------------------------------------
    analytics_file: str = "output/analytics.json"
    youtube_data_api_key: str = ""

    # ---- Misc --------------------------------------------------------------
    dry_run: bool = False
    log_level: str = "INFO"

    # -----------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineConfig":
        """Build a PipelineConfig from a plain dictionary (e.g. loaded JSON)."""
        cfg = cls()
        for key, value in data.items():
            if hasattr(cfg, key):
                # Convert lists back to tuples where needed
                if key in ("video_resolution", "placeholder_color") and isinstance(value, list):
                    value = tuple(value)
                setattr(cfg, key, value)
        return cfg

    @classmethod
    def from_json(cls, path: str) -> "PipelineConfig":
        """Load a PipelineConfig from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        """Serialize the config to a JSON-compatible dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, tuple):
                value = list(value)
            result[key] = value
        return result

    def save_json(self, path: str) -> None:
        """Persist the config to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    def ensure_dirs(self) -> None:
        """Create all required output directories."""
        for attr in (
            "base_dir", "scripts_dir", "audio_dir",
            "thumbnails_dir", "videos_dir", "logs_dir",
        ):
            Path(getattr(self, attr)).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Lazy imports of components (keeps startup fast; errors surface at runtime)
# ---------------------------------------------------------------------------

def _import_component(module_path: str, class_name: str):
    """Dynamically import a component class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def _safe_import(module_path: str, class_name: str, fallback=None):
    """Try to import a component; return fallback stub on ImportError."""
    try:
        return _import_component(module_path, class_name)
    except (ImportError, ModuleNotFoundError) as exc:
        logger.debug("Could not import %s.%s: %s", module_path, class_name, exc)
        return fallback


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """
    Orchestrates the full faceless YouTube video production workflow.

    Typical usage::

        config = PipelineConfig.from_json("config.json")
        pipeline = Pipeline(config)
        result = pipeline.produce_video("What happens inside a black hole",
                                        niche="space_science",
                                        style="documentary",
                                        upload=True)
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        config.ensure_dirs()

        # ---- Set up logging ------------------------------------------------
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    Path(config.logs_dir) / "pipeline.log", encoding="utf-8"
                ),
            ],
        )

        # ---- Initialise all components -------------------------------------
        self._script_gen = self._init_component(
            "faceless_youtube.script_generator", "ScriptGenerator", config
        )
        self._tts = self._init_component(
            "faceless_youtube.tts_engine", "TTSEngine", config
        )
        self._thumb_gen = self._init_component(
            "faceless_youtube.thumbnail_generator", "ThumbnailGenerator", config
        )
        self._assembler = self._init_component(
            "faceless_youtube.video_assembler", "VideoAssembler", config
        )
        self._seo = self._init_component(
            "faceless_youtube.seo_optimizer", "SEOOptimizer", config
        )
        self._uploader = self._init_component(
            "faceless_youtube.uploader", "YouTubeUploader", config
        )
        self._scheduler = self._init_component(
            "faceless_youtube.scheduler", "ContentScheduler", config
        )
        self._analytics = self._init_component(
            "faceless_youtube.analytics", "AnalyticsTracker", config
        )

        # ---- Internal state ------------------------------------------------
        self._last_upload_time: Optional[str] = None
        self._produced_count: int = 0

        logger.info("Pipeline initialised (dry_run=%s).", config.dry_run)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _init_component(module_path: str, class_name: str, config: PipelineConfig):
        """Import and instantiate a pipeline component."""
        try:
            cls = _import_component(module_path, class_name)
            return cls(config)
        except (ImportError, ModuleNotFoundError):
            logger.warning(
                "Component %s not found; a stub will be used. "
                "Run the full install to enable this feature.",
                class_name,
            )
            return _ComponentStub(class_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialise %s: %s", class_name, exc)
            return _ComponentStub(class_name)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _slug(self, text: str) -> str:
        """Turn a topic string into a filesystem-safe slug."""
        import re
        slug = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        slug = slug.strip("_")
        return slug[:80]

    # ------------------------------------------------------------------
    # Visual-asset construction (script sections → list[VisualAsset])
    # ------------------------------------------------------------------

    # Zoom motions cycled across sections for visual variety
    _ZOOM_CYCLE = ("slow_in", "slow_out", "pan_left", "pan_right", "pan_up", "pan_down")

    def _build_visual_assets(self, script_data: Any, slug: str) -> list:
        """Turn a script's sections into a list of VisualAsset objects.

        For each section we need one still image plus a duration. When
        ``config.image_backend == "fal"`` we call ``FalImageClient.generate_scene_image``
        with the section's ``visual_notes`` (B-roll direction) as the prompt.
        Any per-section failure (missing lib, missing key, network error)
        falls back to a solid-color placeholder for that section only, so
        one bad request never breaks the whole pipeline.
        """
        from faceless_youtube.video_assembler import VisualAsset  # lazy

        sections = self._extract_sections(script_data)
        if not sections:
            # No structured sections — fall back to a single full-length placeholder
            placeholder = self._build_placeholder_image(slug, index=0)
            total_duration = float(self._extract_total_duration(script_data) or 60.0)
            return [VisualAsset(path=placeholder, duration=total_duration,
                                transition="fade", zoom="slow_in")]

        use_fal = getattr(self.config, "image_backend", "none") == "fal"
        fal_client = self._get_fal_client() if use_fal else None

        assets: list = []
        for idx, section in enumerate(sections):
            prompt = self._section_prompt(section)
            duration = float(self._section_duration(section) or 8.0)
            zoom = self._ZOOM_CYCLE[idx % len(self._ZOOM_CYCLE)]

            image_path: Optional[str] = None
            if fal_client is not None and prompt:
                try:
                    out = str(Path(self.config.assets_dir) / f"{slug}_scene_{idx:02d}.jpeg")
                    image_path = fal_client.generate_scene_image(prompt, output_path=out)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Scene image %d failed (%s: %s); using placeholder.",
                        idx, type(exc).__name__, exc,
                    )

            if not image_path:
                image_path = self._build_placeholder_image(slug, index=idx)

            assets.append(VisualAsset(
                path=image_path,
                duration=duration,
                transition="fade",
                zoom=zoom,
            ))

        logger.info("Built %d visual asset(s) (backend=%s)",
                    len(assets), getattr(self.config, "image_backend", "none"))
        return assets

    def _get_fal_client(self):
        """Instantiate FalImageClient lazily; return None if unavailable."""
        try:
            from faceless_youtube.fal_image_client import FalImageClient
            return FalImageClient(self.config)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FalImageClient unavailable (%s: %s); using placeholders.",
                           type(exc).__name__, exc)
            return None

    @staticmethod
    def _extract_sections(script_data: Any) -> list:
        """Return a list of section-like objects from either a dict or VideoScript."""
        if script_data is None:
            return []
        if hasattr(script_data, "sections"):
            return list(script_data.sections or [])
        if isinstance(script_data, dict):
            return list(script_data.get("sections") or [])
        return []

    @staticmethod
    def _extract_total_duration(script_data: Any) -> Optional[float]:
        if hasattr(script_data, "total_duration_seconds"):
            return script_data.total_duration_seconds
        if isinstance(script_data, dict):
            return (script_data.get("estimated_duration_seconds")
                    or script_data.get("total_duration_seconds"))
        return None

    @staticmethod
    def _section_prompt(section: Any) -> str:
        """Prefer visual_notes (explicit B-roll direction); fall back to narration."""
        if isinstance(section, dict):
            return (section.get("visual_notes") or section.get("narration")
                    or section.get("heading") or "").strip()
        return (getattr(section, "visual_notes", None)
                or getattr(section, "narration", None)
                or getattr(section, "heading", "") or "").strip()

    @staticmethod
    def _section_duration(section: Any) -> Optional[float]:
        if isinstance(section, dict):
            return section.get("duration_seconds") or section.get("duration")
        return getattr(section, "duration_seconds", None) or getattr(section, "duration", None)

    def _build_placeholder_image(self, slug: str, index: int) -> str:
        """Render a simple solid-color placeholder JPG for one section."""
        from PIL import Image  # lazy
        w, h = 1920, 1080
        # Gently shift hue per index so consecutive slides aren't identical
        palette = [
            (15, 15, 30), (30, 15, 40), (20, 25, 50),
            (40, 20, 30), (25, 35, 45), (35, 25, 20),
        ]
        color = palette[index % len(palette)]
        out_dir = Path(self.config.assets_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{slug}_placeholder_{index:02d}.jpg"
        Image.new("RGB", (w, h), color).save(out_path, "JPEG", quality=90)
        return str(out_path)

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def produce_video(
        self,
        topic: str,
        niche: str = None,
        style: str = "documentary",
        upload: bool = False,
        thumbnail_preset: int = 1,
    ) -> dict:
        """
        Execute the full production pipeline for a single topic.

        Parameters
        ----------
        topic:
            The subject of the video (e.g. "What happens inside a black hole").
        niche:
            Content niche used to tailor the script and SEO metadata
            (e.g. "space_science").  Defaults to ``config.default_niche``.
        style:
            Narrative style passed to the script generator.
            Common values: ``"documentary"``, ``"explainer"``, ``"storytelling"``.
        upload:
            When ``True`` (and ``config.dry_run`` is ``False``), upload the
            finished video and thumbnail to YouTube.
        thumbnail_preset:
            Which thumbnail visual preset to use (1-indexed).

        Returns
        -------
        dict
            A result dictionary containing paths to all generated assets and
            the YouTube video metadata (or a dry-run summary).
        """
        niche = niche or self.config.default_niche
        slug = self._slug(topic)
        started_at = self._timestamp()

        logger.info("--- Producing video: %r (niche=%s, style=%s) ---", topic, niche, style)

        result: dict[str, Any] = {
            "topic": topic,
            "niche": niche,
            "style": style,
            "slug": slug,
            "started_at": started_at,
            "dry_run": self.config.dry_run,
            "steps": {},
        }

        try:
            # ----------------------------------------------------------
            # Step 1 – Generate script
            # ----------------------------------------------------------
            logger.info("Step 1/6 – Generating script …")
            if self.config.dry_run:
                script_data = {
                    "title": f"[DRY RUN] {topic}",
                    "script": "[dry-run script placeholder]",
                    "hook": "[hook]",
                    "sections": [],
                    "call_to_action": "[CTA]",
                    "word_count": 0,
                    "estimated_duration_seconds": 0,
                }
            else:
                script_data = self._script_gen.generate(
                    topic=topic, niche=niche, style=style
                )
            result["script"] = script_data
            result["steps"]["script"] = "ok"
            logger.info("Script generated: %d words.", script_data.get("word_count", 0))

            # ----------------------------------------------------------
            # Step 2 – Generate voiceover (TTS)
            # ----------------------------------------------------------
            logger.info("Step 2/6 – Generating voiceover …")
            audio_path = str(
                Path(self.config.audio_dir) / f"{slug}.mp3"
            )
            if self.config.dry_run:
                logger.info("  [dry-run] TTS skipped → %s", audio_path)
            else:
                audio_path = self._tts.synthesize(
                    text=script_data["script"],
                    output_path=audio_path,
                )
            result["audio_path"] = audio_path
            result["steps"]["tts"] = "ok"

            # ----------------------------------------------------------
            # Step 3 – Generate thumbnail
            # ----------------------------------------------------------
            logger.info("Step 3/6 – Generating thumbnail …")
            thumbnail_path = str(
                Path(self.config.thumbnails_dir) / f"{slug}_thumb.jpg"
            )
            # Derive a short thumbnail text from the title
            thumb_title = script_data.get("title", topic)
            if self.config.dry_run:
                logger.info("  [dry-run] Thumbnail skipped → %s", thumbnail_path)
            else:
                thumbnail_path = self._thumb_gen.generate(
                    title=thumb_title,
                    topic=topic,
                    niche=niche,
                    preset=thumbnail_preset,
                    output_path=thumbnail_path,
                )
            result["thumbnail_path"] = thumbnail_path
            result["steps"]["thumbnail"] = "ok"

            # ----------------------------------------------------------
            # Step 4 – Assemble video
            # ----------------------------------------------------------
            logger.info("Step 4/6 – Assembling video …")
            video_path = str(
                Path(self.config.videos_dir) / f"{slug}.mp4"
            )
            if self.config.dry_run:
                logger.info("  [dry-run] Assembly skipped → %s", video_path)
            else:
                visual_assets = self._build_visual_assets(script_data, slug)
                result["visual_asset_count"] = len(visual_assets)
                video_path = self._assembler.assemble(
                    audio_path=audio_path,
                    visual_assets=visual_assets,
                    output_path=video_path,
                )
            result["video_path"] = video_path
            result["steps"]["assembly"] = "ok"

            # ----------------------------------------------------------
            # Step 5 – SEO optimisation
            # ----------------------------------------------------------
            logger.info("Step 5/6 – Optimising metadata …")
            if self.config.dry_run:
                seo_data = {
                    "title": script_data.get("title", topic),
                    "description": "[dry-run description]",
                    "tags": ["dry", "run"],
                }
            else:
                seo_data = self._seo.optimize(
                    topic=topic,
                    niche=niche,
                    script=script_data["script"],
                    title=script_data.get("title", topic),
                )
            result["seo"] = seo_data
            result["steps"]["seo"] = "ok"
            logger.info("SEO title: %r", seo_data.get("title"))

            # ----------------------------------------------------------
            # Step 6 – Optional upload
            # ----------------------------------------------------------
            if upload:
                logger.info("Step 6/6 – Uploading to YouTube …")
                if self.config.dry_run:
                    upload_result = {
                        "video_id": "DRY_RUN_ID",
                        "url": "https://youtube.com/watch?v=DRY_RUN_ID",
                        "status": "dry_run",
                    }
                    logger.info("  [dry-run] Upload skipped.")
                else:
                    upload_result = self._uploader.upload(
                        video_path=video_path,
                        thumbnail_path=thumbnail_path,
                        title=seo_data.get("title", topic),
                        description=seo_data.get("description", ""),
                        tags=seo_data.get("tags", []),
                    )
                result["upload"] = upload_result
                result["steps"]["upload"] = "ok"
                self._last_upload_time = self._timestamp()
                logger.info("Uploaded: %s", upload_result.get("url"))
            else:
                result["steps"]["upload"] = "skipped"

            # ----------------------------------------------------------
            # Record in analytics tracker
            # ----------------------------------------------------------
            if not self.config.dry_run:
                self._analytics.record_production(
                    topic=topic,
                    niche=niche,
                    video_id=result.get("upload", {}).get("video_id"),
                    paths=result,
                )

            self._produced_count += 1
            result["finished_at"] = self._timestamp()
            result["success"] = True
            logger.info("Video production complete: %r", topic)

        except Exception as exc:  # noqa: BLE001
            result["success"] = False
            result["error"] = str(exc)
            result["traceback"] = traceback.format_exc()
            result["finished_at"] = self._timestamp()
            logger.error("Pipeline failed for %r: %s", topic, exc, exc_info=True)

        return result

    # ------------------------------------------------------------------

    def produce_batch(
        self,
        topics: list[str],
        niche: str = None,
        style: str = "documentary",
        upload: bool = False,
    ) -> list[dict]:
        """
        Process a list of topics sequentially, returning a result dict for each.

        Parameters
        ----------
        topics:
            Ordered list of topic strings to produce.
        niche:
            Shared content niche for all topics.
        style:
            Shared narrative style for all topics.
        upload:
            Whether to upload each video upon completion.

        Returns
        -------
        list[dict]
            One result dictionary per topic (same format as ``produce_video``).
        """
        logger.info("Batch production: %d topics (niche=%s).", len(topics), niche)
        results = []
        for index, topic in enumerate(topics, start=1):
            logger.info("Batch progress: %d/%d – %r", index, len(topics), topic)
            result = self.produce_video(
                topic=topic, niche=niche, style=style, upload=upload
            )
            results.append(result)
        logger.info(
            "Batch complete. Successes: %d / %d.",
            sum(1 for r in results if r.get("success")),
            len(results),
        )
        return results

    # ------------------------------------------------------------------

    def run_scheduled(self) -> list[dict]:
        """
        Fetch all due items from the ContentScheduler and produce them.

        Returns
        -------
        list[dict]
            Result dicts for every item that was due and processed.
        """
        logger.info("Checking schedule for due items …")
        due_items = self._scheduler.get_due_items()
        if not due_items:
            logger.info("No items currently due.")
            return []

        logger.info("%d scheduled item(s) are due.", len(due_items))
        results = []
        for item in due_items:
            topic = item.get("topic", "Unknown topic")
            niche = item.get("niche", self.config.default_niche)
            style = item.get("style", "documentary")
            preset = item.get("thumbnail_preset", 1)

            result = self.produce_video(
                topic=topic,
                niche=niche,
                style=style,
                upload=True,
                thumbnail_preset=preset,
            )
            # Mark the scheduled item as processed
            if result.get("success") and not self.config.dry_run:
                self._scheduler.mark_complete(item.get("id"))
            results.append(result)
        return results

    # ------------------------------------------------------------------

    def run_daily(self) -> dict:
        """
        Perform the standard daily automation cycle:
          1. Check the schedule for due videos.
          2. Produce and upload them.
          3. Refresh analytics for recently uploaded videos.
          4. Return a summary dictionary.

        Returns
        -------
        dict
            Summary with counts of produced/uploaded videos and any errors.
        """
        logger.info("=== Daily run started ===")
        started_at = self._timestamp()
        results = self.run_scheduled()

        # Refresh analytics for any video uploaded in the last 48 h
        refreshed = 0
        if not self.config.dry_run:
            try:
                refreshed = self._analytics.refresh_recent(hours=48)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Analytics refresh failed: %s", exc)

        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]

        summary = {
            "started_at": started_at,
            "finished_at": self._timestamp(),
            "due_count": len(results),
            "success_count": len(successes),
            "failure_count": len(failures),
            "analytics_refreshed": refreshed,
            "results": results,
        }
        logger.info(
            "=== Daily run complete: %d succeeded, %d failed ===",
            len(successes),
            len(failures),
        )
        return summary

    # ------------------------------------------------------------------

    def status(self) -> dict:
        """
        Return a snapshot of the current pipeline state.

        Returns
        -------
        dict
            Keys: queue_length, last_upload, next_scheduled, produced_this_session,
            dry_run, components.
        """
        # Queue length from scheduler
        try:
            queue_length = self._scheduler.queue_length()
        except Exception:  # noqa: BLE001
            queue_length = -1

        # Next scheduled item
        try:
            next_item = self._scheduler.next_scheduled()
        except Exception:  # noqa: BLE001
            next_item = None

        # Analytics summary
        try:
            analytics_summary = self._analytics.summary()
        except Exception:  # noqa: BLE001
            analytics_summary = {}

        # Component health
        components = {
            name: ("stub" if isinstance(obj, _ComponentStub) else "ok")
            for name, obj in [
                ("script_generator", self._script_gen),
                ("tts_engine", self._tts),
                ("thumbnail_generator", self._thumb_gen),
                ("video_assembler", self._assembler),
                ("seo_optimizer", self._seo),
                ("youtube_uploader", self._uploader),
                ("content_scheduler", self._scheduler),
                ("analytics_tracker", self._analytics),
            ]
        }

        return {
            "queue_length": queue_length,
            "last_upload": self._last_upload_time,
            "next_scheduled": next_item,
            "produced_this_session": self._produced_count,
            "dry_run": self.config.dry_run,
            "components": components,
            "analytics": analytics_summary,
            "timestamp": self._timestamp(),
        }


# ---------------------------------------------------------------------------
# Stub – used when a component module is not installed
# ---------------------------------------------------------------------------

class _ComponentStub:
    """
    Placeholder object returned when a component module cannot be imported.

    Every method call logs a warning and returns a sensible empty value so
    that the rest of the pipeline can still report status / dry-run safely.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, attr: str):
        def _stub(*args, **kwargs):
            logger.warning(
                "Component '%s' is not installed – call to .%s() is a no-op.",
                self._name, attr,
            )
            # Return sensible defaults based on expected return types
            if attr in ("generate", "optimize"):
                return {
                    "title": args[0] if args else "Untitled",
                    "script": "",
                    "description": "",
                    "tags": [],
                    "hook": "",
                    "sections": [],
                    "call_to_action": "",
                    "word_count": 0,
                    "estimated_duration_seconds": 0,
                }
            if attr == "synthesize":
                return kwargs.get("output_path", "")
            if attr == "assemble":
                return kwargs.get("output_path", "")
            if attr in ("upload",):
                return {"video_id": None, "url": None, "status": "stub"}
            if attr in ("get_due_items",):
                return []
            if attr in ("queue_length", "refresh_recent"):
                return 0
            if attr in ("next_scheduled",):
                return None
            if attr in ("summary",):
                return {}
            return None
        return _stub
