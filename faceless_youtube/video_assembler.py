"""
faceless_youtube/video_assembler.py

Assembles faceless YouTube videos using FFmpeg via subprocess.
No Python FFmpeg wrappers \u2014 all media operations are delegated directly
to the ffmpeg / ffprobe binaries.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Minimal pipeline configuration consumed by VideoAssembler."""

    resolution_width: int = 1920
    resolution_height: int = 1080
    fps: int = 30
    video_format: str = "mp4"
    output_dir: str = "output"
    temp_dir: str = "temp"


@dataclass
class VisualAsset:
    """A single visual element (image or video clip) used in the assembly."""

    path: str
    duration: float
    transition: str = "fade"   # "fade" | "fade_black" | "cut"
    zoom: str = "slow_in"      # "slow_in" | "slow_out" | "pan_left" | "pan_right" | "pan_up" | "pan_down" | "none"


@dataclass
class SubtitleEntry:
    """One subtitle cue."""

    start: float   # seconds
    end: float     # seconds
    text: str


class VideoAssembler:
    """
    Assembles faceless YouTube videos with Ken Burns effects, transitions,
    subtitle burning, background music, intro/outro, and a full pipeline helper.
    """

    def __init__(self, config) -> None:
        self.config = config
        self._check_ffmpeg()
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(config.temp_dir).mkdir(parents=True, exist_ok=True)

    # Public API

    def assemble(
        self,
        audio_path: str,
        visual_assets: list,
        output_path: str | None = None,
        subtitles_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("assembled")
        images = [a.path for a in visual_assets]
        durations = [a.duration for a in visual_assets]

        raw_slideshow = self._tmp_path("slideshow_raw", "mp4")
        self._build_slideshow_cmd(
            images=images,
            durations=durations,
            assets=visual_assets,
            output_path=raw_slideshow,
        )

        with_audio = self._tmp_path("with_audio", "mp4")
        cmd = self._build_audio_merge_cmd(
            video_path=raw_slideshow,
            audio_path=audio_path,
            output_path=with_audio,
        )
        self._run_ffmpeg(cmd)

        if subtitles_path:
            cmd = self._build_subtitle_cmd(
                video_path=with_audio,
                subtitles_path=subtitles_path,
                output_path=output_path,
                style="modern",
            )
            self._run_ffmpeg(cmd)
        else:
            shutil.move(with_audio, output_path)

        logger.info("Assembly complete: %s", output_path)
        return output_path

    def create_slideshow(
        self,
        images: list,
        durations: list,
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("slideshow")
        assets = [VisualAsset(path=img, duration=dur) for img, dur in zip(images, durations)]
        self._build_slideshow_cmd(
            images=images,
            durations=durations,
            assets=assets,
            output_path=output_path,
        )
        logger.info("Slideshow created: %s", output_path)
        return output_path

    def add_subtitles(
        self,
        video_path: str,
        subtitles: list,
        output_path: str | None = None,
        style: str = "modern",
    ) -> str:
        output_path = output_path or self._default_output("subtitled")
        srt_path = self._write_srt(subtitles)
        cmd = self._build_subtitle_cmd(
            video_path=video_path,
            subtitles_path=srt_path,
            output_path=output_path,
            style=style,
        )
        self._run_ffmpeg(cmd)
        logger.info("Subtitles burned: %s", output_path)
        return output_path

    def add_background_music(
        self,
        video_path: str,
        music_path: str,
        volume: float = 0.1,
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("with_music")
        video_dur = self._get_media_duration(video_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex",
            (
                f"[1:a]volume={volume},atrim=duration={video_dur}[music];"
                "[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[aout]"
            ),
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ]
        self._run_ffmpeg(cmd)
        logger.info("Background music added: %s", output_path)
        return output_path

    def add_intro(
        self,
        video_path: str,
        intro_path: str,
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("with_intro")
        return self.concatenate_videos([intro_path, video_path], output_path)

    def add_outro(
        self,
        video_path: str,
        outro_duration: float = 5.0,
        text: str = "Subscribe!",
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("with_outro")
        outro_path = self._tmp_path("outro", "mp4")
        w = self.config.resolution_width
        h = self.config.resolution_height
        fps = self.config.fps

        safe_text = text.replace("'", r"\'").replace(":", r"\:")

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={w}x{h}:r={fps}:d={outro_duration}",
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", (
                f"drawtext=text='{safe_text}':"
                "fontcolor=white:fontsize=72:"
                "x=(w-text_w)/2:y=(h-text_h)/2"
            ),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(outro_duration),
            "-pix_fmt", "yuv420p",
            outro_path,
        ]
        self._run_ffmpeg(cmd)
        result = self.concatenate_videos([video_path, outro_path], output_path)
        logger.info("Outro added: %s", output_path)
        return result

    def concatenate_videos(
        self,
        video_paths: list,
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("concatenated")

        list_file = self._tmp_path("concat_list", "txt")
        with open(list_file, "w") as fh:
            for vp in video_paths:
                abs_path = os.path.abspath(vp)
                fh.write(f"file '{abs_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        self._run_ffmpeg(cmd)
        logger.info("Concatenation complete: %s", output_path)
        return output_path

    def full_pipeline(
        self,
        audio_path: str,
        images: list,
        section_durations: list,
        subtitles: list | None = None,
        music_path: str | None = None,
        output_path: str | None = None,
    ) -> str:
        output_path = output_path or self._default_output("final")

        slideshow_path = self._tmp_path("pipeline_slideshow", "mp4")
        assets = [VisualAsset(path=img, duration=dur) for img, dur in zip(images, section_durations)]
        self._build_slideshow_cmd(
            images=images,
            durations=section_durations,
            assets=assets,
            output_path=slideshow_path,
        )

        with_narration = self._tmp_path("pipeline_narration", "mp4")
        cmd = self._build_audio_merge_cmd(
            video_path=slideshow_path,
            audio_path=audio_path,
            output_path=with_narration,
        )
        self._run_ffmpeg(cmd)
        current = with_narration

        if subtitles:
            srt_path = self._write_srt(subtitles)
            with_subs = self._tmp_path("pipeline_subs", "mp4")
            cmd = self._build_subtitle_cmd(
                video_path=current,
                subtitles_path=srt_path,
                output_path=with_subs,
                style="modern",
            )
            self._run_ffmpeg(cmd)
            current = with_subs

        if music_path:
            with_music = self._tmp_path("pipeline_music", "mp4")
            self.add_background_music(
                video_path=current,
                music_path=music_path,
                volume=0.1,
                output_path=with_music,
            )
            current = with_music

        shutil.move(current, output_path)
        logger.info("Full pipeline complete: %s", output_path)
        return output_path

    @staticmethod
    def generate_subtitles_from_text(
        text: str,
        audio_duration: float,
        words_per_chunk: int = 6,
    ) -> list:
        words = text.split()
        if not words:
            return []

        chunks: list = []
        for i in range(0, len(words), words_per_chunk):
            chunk = " ".join(words[i : i + words_per_chunk])
            chunks.append(chunk)

        chunk_duration = audio_duration / len(chunks)
        entries: list = []
        for idx, chunk in enumerate(chunks):
            start = idx * chunk_duration
            end = start + chunk_duration
            entries.append(SubtitleEntry(start=start, end=end, text=chunk))

        return entries

    # FFmpeg command builders

    def _build_slideshow_cmd(
        self,
        images: list,
        durations: list,
        assets: list,
        output_path: str,
    ) -> None:
        if len(images) != len(durations):
            raise ValueError("images and durations must be the same length")
        if not images:
            raise ValueError("At least one image is required")

        w = self.config.resolution_width
        h = self.config.resolution_height
        fps = self.config.fps

        clip_paths: list = []
        for idx, (img, dur, asset) in enumerate(zip(images, durations, assets)):
            clip_path = self._tmp_path(f"clip_{idx:04d}", "mp4")
            vf = self._ken_burns_filter(asset.zoom, dur, w, h)
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", img,
                "-vf", vf,
                "-t", str(dur),
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                clip_path,
            ]
            self._run_ffmpeg(cmd)
            clip_paths.append(clip_path)

        if len(clip_paths) == 1:
            shutil.copy(clip_paths[0], output_path)
            return

        use_xfade = all(a.transition in ("fade", "fade_black") for a in assets)

        if use_xfade:
            self._concat_with_xfade(clip_paths, assets, output_path)
        else:
            self.concatenate_videos(clip_paths, output_path)

    def _concat_with_xfade(
        self,
        clip_paths: list,
        assets: list,
        output_path: str,
    ) -> None:
        transition_duration = 0.5

        clip_durations = [self._get_media_duration(p) for p in clip_paths]

        input_args: list = []
        for cp in clip_paths:
            input_args += ["-i", cp]

        filter_parts: list = []
        offset = 0.0
        prev_label = "[0:v]"

        for i in range(1, len(clip_paths)):
            offset += clip_durations[i - 1] - transition_duration
            offset = max(offset, 0.0)
            next_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
            transition = (
                "fade"
                if assets[i - 1].transition == "fade"
                else "fadeblack"
            )
            filter_parts.append(
                f"{prev_label}[{i}:v]xfade=transition={transition}:"
                f"duration={transition_duration}:offset={offset}{next_label}"
            )
            prev_label = f"[v{i}]"

        filter_complex = ";".join(filter_parts)

        cmd = (
            ["ffmpeg", "-y"]
            + input_args
            + [
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                output_path,
            ]
        )
        self._run_ffmpeg(cmd)

    def _build_audio_merge_cmd(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> list:
        return [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ]

    def _build_subtitle_cmd(
        self,
        video_path: str,
        subtitles_path: str,
        output_path: str,
        style: str = "modern",
    ) -> list:
        abs_srt = os.path.abspath(subtitles_path)
        escaped_srt = abs_srt.replace("\\", "/").replace(":", "\\:")

        if style == "highlight":
            force_style = (
                "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFF00,"
                "OutlineColour=&H00000000,BackColour=&H80000000,"
                "Bold=1,Outline=2,Shadow=1,Alignment=2,"
                "MarginV=40"
            )
        else:
            force_style = (
                "FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BackColour=&H80000000,"
                "Bold=0,Outline=2,Shadow=1,Alignment=2,"
                "MarginV=40"
            )

        return [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{escaped_srt}':force_style='{force_style}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    # FFmpeg / ffprobe utilities

    def _run_ffmpeg(self, cmd: list):
        logger.debug("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg command failed (exit {result.returncode}).\n"
                f"Command: {' '.join(cmd)}\n"
                f"Stderr:\n{result.stderr}"
            )
        return result

    def _check_ffmpeg(self) -> None:
        for binary in ("ffmpeg", "ffprobe"):
            if shutil.which(binary) is None:
                raise EnvironmentError(
                    f"'{binary}' not found on PATH. "
                    "Please install FFmpeg: https://ffmpeg.org/download.html"
                )

    def _get_media_duration(self, path: str) -> float:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed for '{path}'.\nStderr:\n{result.stderr}"
            )
        info = json.loads(result.stdout)
        try:
            return float(info["format"]["duration"])
        except (KeyError, ValueError) as exc:
            raise RuntimeError(
                f"Could not determine duration of '{path}': {exc}"
            ) from exc

    @staticmethod
    def _ken_burns_filter(
        zoom: str,
        duration: float,
        width: int,
        height: int,
    ) -> str:
        fps = 30
        total_frames = max(int(duration * fps), 1)

        if zoom == "none":
            return (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
            )

        if zoom == "slow_in":
            return (
                "zoompan="
                "z='min(zoom+0.0003,1.1)':"
                "x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        if zoom == "slow_out":
            return (
                "zoompan="
                "z='if(eq(on,1),1.1,max(zoom-0.0003,1.0))':"
                "x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        if zoom == "pan_left":
            return (
                "zoompan="
                "z='1.08':"
                f"x='iw*0.08*(1-on/{total_frames})':"
                "y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        if zoom == "pan_right":
            return (
                "zoompan="
                "z='1.08':"
                f"x='iw*0.08*(on/{total_frames})':"
                "y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        if zoom == "pan_up":
            return (
                "zoompan="
                "z='1.08':"
                "x='iw/2-(iw/zoom/2)':"
                f"y='ih*0.08*(1-on/{total_frames})':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        if zoom == "pan_down":
            return (
                "zoompan="
                "z='1.08':"
                "x='iw/2-(iw/zoom/2)':"
                f"y='ih*0.08*(on/{total_frames})':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
            )

        return VideoAssembler._ken_burns_filter("slow_in", duration, width, height)

    @staticmethod
    def _write_srt(subtitles: list, path: str | None = None) -> str:
        if path is None:
            path = os.path.join(
                tempfile.gettempdir(),
                f"subtitles_{uuid.uuid4().hex}.srt",
            )

        def _fmt_time(seconds: float) -> str:
            ms = int(round(seconds * 1000))
            hh = ms // 3_600_000
            ms %= 3_600_000
            mm = ms // 60_000
            ms %= 60_000
            ss = ms // 1_000
            ms %= 1_000
            return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

        lines: list = []
        for idx, entry in enumerate(subtitles, start=1):
            lines.append(str(idx))
            lines.append(f"{_fmt_time(entry.start)} --> {_fmt_time(entry.end)}")
            lines.append(entry.text)
            lines.append("")

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        return path

    def _default_output(self, tag: str) -> str:
        uid = uuid.uuid4().hex[:8]
        return os.path.join(
            self.config.output_dir,
            f"{tag}_{uid}.{self.config.video_format}",
        )

    def _tmp_path(self, tag: str, ext: str) -> str:
        uid = uuid.uuid4().hex[:8]
        return os.path.join(self.config.temp_dir, f"{tag}_{uid}.{ext}")


def generate_subtitles_from_text(
    text: str,
    audio_duration: float,
    words_per_chunk: int = 6,
) -> list:
    return VideoAssembler.generate_subtitles_from_text(
        text=text,
        audio_duration=audio_duration,
        words_per_chunk=words_per_chunk,
    )
