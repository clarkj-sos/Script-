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


def _import_component(module_path: str, class_name: str):
    """Dynamically import a component class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


class Pipeline:
    """
    Orchestrates the full faceless YouTube video production workflow.

    Typical usage::

        config = PipelineConfig.from_file("config.json")
        pipeline = Pipeline(config)
        result = pipeline.produce_video("What happens inside a black hole",
                                        niche="space_science",
                                        style="documentary",
                                        upload=True)
    """

    def __init__(self, config) -> None:
        self.config = config
        if hasattr(config, "ensure_directories"):
            config.ensure_directories()

        # Set up logging
        log_level = getattr(config, "log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        # Initialise all components
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
        self.scheduler = self._init_component(
            "faceless_youtube.scheduler", "ContentScheduler", config
        )
        self._analytics = self._init_component(
            "faceless_youtube.analytics", "AnalyticsTracker", config
        )

        # Internal state
        self._last_upload_time: Optional[str] = None
        self._produced_count: int = 0

        dry_run = getattr(config, "dry_run", False)
        logger.info("Pipeline initialised (dry_run=%s).", dry_run)

    @staticmethod
    def _init_component(module_path: str, class_name: str, config):
        """Import and instantiate a pipeline component."""
        try:
            cls = _import_component(module_path, class_name)
            return cls(config)
        except (ImportError, ModuleNotFoundError) as exc:
            logger.warning(
                "Component %s not found (%s); a stub will be used.",
                class_name, exc,
            )
            return _ComponentStub(class_name)
        except Exception as exc:
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

    def produce_video(
        self,
        topic: str,
        niche: str = None,
        style: str = "documentary",
        upload: bool = False,
        thumbnail_preset: int = 1,
    ) -> dict:
        """Execute the full production pipeline for a single topic."""
        niche = niche or getattr(self.config, "default_niche", "general")
        slug = self._slug(topic)
        started_at = self._timestamp()
        dry_run = getattr(self.config, "dry_run", False)

        logger.info("--- Producing video: %r (niche=%s, style=%s) ---", topic, niche, style)

        result: dict[str, Any] = {
            "topic": topic,
            "niche": niche,
            "style": style,
            "slug": slug,
            "started_at": started_at,
            "dry_run": dry_run,
            "steps": {},
        }

        try:
            # Step 1 - Generate script
            logger.info("Step 1/6 - Generating script ...")
            if dry_run:
                script_data = {
                    "title": f"[DRY RUN] {topic}",
                    "script": "[dry-run script placeholder]",
                    "word_count": 0,
                    "sections": [],
                }
            else:
                script = self._script_gen.generate_script(topic=topic, style=style)
                # Convert to dict-like structure
                if hasattr(script, "to_dict"):
                    script_data = script.to_dict()
                    script_data["script"] = " ".join(
                        [script.hook] + [s.narration for s in script.sections] + [script.outro]
                    )
                    script_data["word_count"] = script.word_count()
                else:
                    script_data = script
            result["script"] = script_data
            result["steps"]["script"] = "ok"
            logger.info("Script generated: %d words.", script_data.get("word_count", 0))

            # Step 2 - Generate voiceover (TTS)
            logger.info("Step 2/6 - Generating voiceover ...")
            output_dir = getattr(self.config, "output_dir", "output")
            audio_path = str(Path(output_dir) / "audio" / f"{slug}.mp3")
            Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
            if dry_run:
                logger.info("  [dry-run] TTS skipped -> %s", audio_path)
            else:
                audio_path = self._tts.synthesize(
                    text=script_data.get("script", ""),
                    output_path=audio_path,
                )
            result["audio_path"] = audio_path
            result["steps"]["tts"] = "ok"

            # Step 3 - Generate thumbnail
            logger.info("Step 3/6 - Generating thumbnail ...")
            thumbnail_path = str(Path(output_dir) / "thumbnails" / f"{slug}_thumb.jpg")
            Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
            thumb_title = script_data.get("title", topic)
            if dry_run:
                logger.info("  [dry-run] Thumbnail skipped -> %s", thumbnail_path)
            else:
                thumbnail_path = self._thumb_gen.generate(
                    text=thumb_title,
                    preset=thumbnail_preset,
                    output_path=thumbnail_path,
                )
            result["thumbnail_path"] = thumbnail_path
            result["steps"]["thumbnail"] = "ok"

            # Step 4 - Assemble video (placeholder; requires visual assets)
            logger.info("Step 4/6 - Assembling video ...")
            video_path = str(Path(output_dir) / "videos" / f"{slug}.mp4")
            Path(video_path).parent.mkdir(parents=True, exist_ok=True)
            if dry_run:
                logger.info("  [dry-run] Assembly skipped -> %s", video_path)
            else:
                # In a full setup, fetch stock footage here. For now use thumbnail as placeholder.
                try:
                    from faceless_youtube.video_assembler import VisualAsset
                    assets = [VisualAsset(path=thumbnail_path,
                                          duration=max(5.0, script_data.get("total_duration_seconds", 30) / 1.0))]
                    video_path = self._assembler.assemble(
                        audio_path=audio_path,
                        visual_assets=assets,
                        output_path=video_path,
                    )
                except Exception as exc:
                    logger.warning("Video assembly skipped: %s", exc)
                    video_path = None
            result["video_path"] = video_path
            result["steps"]["assembly"] = "ok" if video_path else "skipped"

            # Step 5 - SEO optimisation
            logger.info("Step 5/6 - Optimising metadata ...")
            if dry_run:
                seo_data = {
                    "title": script_data.get("title", topic),
                    "description": "[dry-run description]",
                    "tags": ["dry", "run"],
                }
            else:
                try:
                    seo_data = self._seo.build_full_metadata(
                        title=script_data.get("title", topic),
                        description=script_data.get("description", ""),
                        tags=script_data.get("tags", []),
                        niche=niche,
                    )
                except Exception as exc:
                    logger.warning("SEO optimisation failed: %s", exc)
                    seo_data = {
                        "title": script_data.get("title", topic),
                        "description": script_data.get("description", ""),
                        "tags": script_data.get("tags", []),
                    }
            result["seo"] = seo_data
            result["steps"]["seo"] = "ok"

            # Step 6 - Optional upload
            if upload and video_path:
                logger.info("Step 6/6 - Uploading to YouTube ...")
                if dry_run:
                    upload_result = {
                        "video_id": "DRY_RUN_ID",
                        "url": "https://youtube.com/watch?v=DRY_RUN_ID",
                    }
                    logger.info("  [dry-run] Upload skipped.")
                else:
                    upload_result = self._uploader.upload_video(
                        file_path=video_path,
                        title=seo_data.get("optimized_title", seo_data.get("title", topic)),
                        description=seo_data.get("optimized_description", seo_data.get("description", "")),
                        tags=seo_data.get("optimized_tags", seo_data.get("tags", [])),
                        privacy=getattr(self.config, "privacy_status", "private"),
                        thumbnail_path=thumbnail_path,
                    )
                result["upload"] = upload_result
                result["steps"]["upload"] = "ok"
                self._last_upload_time = self._timestamp()
                # Record analytics
                if not dry_run and isinstance(upload_result, dict) and upload_result.get("video_id"):
                    try:
                        self._analytics.record_upload(
                            video_id=upload_result["video_id"],
                            title=seo_data.get("optimized_title", topic),
                            topic=topic,
                            niche=niche,
                        )
                    except Exception as exc:
                        logger.warning("Analytics record failed: %s", exc)
                logger.info("Uploaded: %s", upload_result.get("url"))
            else:
                result["steps"]["upload"] = "skipped"

            self._produced_count += 1
            result["finished_at"] = self._timestamp()
            result["success"] = True
            logger.info("Video production complete: %r", topic)

        except Exception as exc:
            result["success"] = False
            result["error"] = str(exc)
            result["traceback"] = traceback.format_exc()
            result["finished_at"] = self._timestamp()
            logger.error("Pipeline failed for %r: %s", topic, exc, exc_info=True)

        return result

    def produce_batch(
        self,
        topics: list,
        niche: str = None,
        style: str = "documentary",
        upload: bool = False,
    ) -> list:
        """Process a list of topics sequentially."""
        logger.info("Batch production: %d topics (niche=%s).", len(topics), niche)
        results = []
        for index, topic in enumerate(topics, start=1):
            logger.info("Batch progress: %d/%d - %r", index, len(topics), topic)
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

    def run_scheduled(self) -> list:
        """Fetch all due items from the scheduler and produce them."""
        logger.info("Checking schedule for due items ...")
        try:
            due_items = self.scheduler.run_due()
        except Exception as exc:
            logger.warning("Scheduler check failed: %s", exc)
            return []

        if not due_items:
            logger.info("No items currently due.")
            return []

        logger.info("%d scheduled item(s) are due.", len(due_items))
        results = []
        for item in due_items:
            topic = getattr(item, "topic", "Unknown topic")
            metadata = getattr(item, "metadata", {}) or {}
            niche = metadata.get("niche", getattr(self.config, "default_niche", "general"))
            style = metadata.get("style", "documentary")
            preset = metadata.get("thumbnail_preset", 1)

            self.scheduler.update_status(topic, "generating")
            result = self.produce_video(
                topic=topic,
                niche=niche,
                style=style,
                upload=True,
                thumbnail_preset=preset,
            )
            new_status = "published" if result.get("success") else "failed"
            self.scheduler.update_status(topic, new_status,
                                          video_path=result.get("video_path"),
                                          thumbnail_path=result.get("thumbnail_path"))
            results.append(result)
        return results

    def run_daily(self) -> dict:
        """Perform the standard daily automation cycle."""
        logger.info("=== Daily run started ===")
        started_at = self._timestamp()
        results = self.run_scheduled()

        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]

        summary = {
            "started_at": started_at,
            "finished_at": self._timestamp(),
            "due_count": len(results),
            "success_count": len(successes),
            "failure_count": len(failures),
            "results": results,
        }
        logger.info(
            "=== Daily run complete: %d succeeded, %d failed ===",
            len(successes),
            len(failures),
        )
        return summary

    def status(self) -> dict:
        """Return a snapshot of the current pipeline state."""
        try:
            queue = self.scheduler.get_schedule()
            queue_length = len([s for s in queue if s.status == "pending"])
        except Exception:
            queue_length = -1

        try:
            next_item = self.scheduler.get_next()
            next_scheduled = next_item.scheduled_date if next_item else None
        except Exception:
            next_scheduled = None

        components = {
            name: ("stub" if isinstance(obj, _ComponentStub) else "ok")
            for name, obj in [
                ("script_generator", self._script_gen),
                ("tts_engine", self._tts),
                ("thumbnail_generator", self._thumb_gen),
                ("video_assembler", self._assembler),
                ("seo_optimizer", self._seo),
                ("uploader", self._uploader),
                ("scheduler", self.scheduler),
                ("analytics", self._analytics),
            ]
        }

        return {
            "queue_length": queue_length,
            "last_upload": self._last_upload_time,
            "next_scheduled": next_scheduled,
            "produced_this_session": self._produced_count,
            "dry_run": getattr(self.config, "dry_run", False),
            "components": components,
            "timestamp": self._timestamp(),
        }


class _ComponentStub:
    """Placeholder for a component that failed to import or initialise."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, attr: str):
        def _stub(*args, **kwargs):
            logger.warning(
                "Component '%s' is not installed - call to .%s() is a no-op.",
                self._name, attr,
            )
            if attr in ("generate", "generate_script", "build_full_metadata"):
                return {"title": "Untitled", "script": "", "sections": [],
                        "description": "", "tags": [], "word_count": 0}
            if attr == "synthesize":
                return kwargs.get("output_path", "")
            if attr == "assemble":
                return kwargs.get("output_path", "")
            if attr == "upload_video":
                return {"video_id": None, "url": None}
            if attr in ("run_due", "get_schedule"):
                return []
            if attr == "get_next":
                return None
            return None
        return _stub
