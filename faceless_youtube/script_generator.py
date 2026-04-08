"""
faceless_youtube/script_generator.py

Script generation module for the faceless YouTube automation pipeline.
Uses the OpenAI Chat Completions API (gpt-4o) via raw httpx calls with
structured JSON output \u2014 no openai package dependency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration consumed by all pipeline stages."""
    openai_api_key: str
    niche: str
    min_script_words: int = 800
    max_script_words: int = 1_500
    target_video_length_minutes: float = 10.0


@dataclass
class ScriptSection:
    """A single named section within a video script."""
    heading: str
    narration: str
    visual_notes: str          # Stock-footage / B-roll direction for editors
    duration_seconds: int


@dataclass
class VideoScript:
    """Complete, ready-to-produce video script."""
    title: str
    hook: str                           # First ~5 seconds \u2014 attention grabber
    sections: list[ScriptSection]
    outro: str
    total_duration_seconds: int
    tags: list[str]
    description: str                    # YouTube description (SEO-optimised)

    def word_count(self) -> int:
        """Approximate narration word count across hook + sections + outro."""
        texts = [self.hook, self.outro] + [s.narration for s in self.sections]
        return sum(len(t.split()) for t in texts)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STYLE_INSTRUCTIONS: dict[str, str] = {
    "documentary": (
        "Write in a calm, authoritative documentary narrator voice. "
        "Use factual framing, historical context, and measured pacing. "
        "Think BBC/National Geographic tone \u2014 credible, immersive, educational."
    ),
    "listicle": (
        "Write in an energetic, punchy listicle style. "
        "Number each key point, use short punchy sentences, build anticipation "
        "between items ('But number 3 will shock you\u2026'). Keep momentum high."
    ),
    "explainer": (
        "Write in a friendly, clear explainer voice. Use analogies and "
        "everyday language to break down complex ideas. Think TED-Ed \u2014 warm, "
        "curious, step-by-step logical flow."
    ),
    "storytelling": (
        "Write as a compelling narrative storyteller. Open in media res, "
        "build tension, use vivid scene-setting, and resolve with a satisfying "
        "emotional or intellectual payoff. Think true-crime podcast meets "
        "long-form journalism."
    ),
    "mystery": (
        "Write in a suspenseful, conspiratorial tone. Pose provocative "
        "questions, withhold answers strategically, layer in surprising "
        "reveals, and leave the audience with an unsettling final thought. "
        "Think 'What if everything you knew was wrong?'"
    ),
}

VALID_STYLES = set(STYLE_INSTRUCTIONS.keys())

SCRIPT_JSON_SCHEMA: dict[str, Any] = {
    "name": "video_script",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "hook": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading":          {"type": "string"},
                        "narration":        {"type": "string"},
                        "visual_notes":     {"type": "string"},
                        "duration_seconds": {"type": "integer"},
                    },
                    "required": ["heading", "narration", "visual_notes", "duration_seconds"],
                    "additionalProperties": False,
                },
            },
            "outro":                  {"type": "string"},
            "total_duration_seconds": {"type": "integer"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "description": {"type": "string"},
        },
        "required": [
            "title", "hook", "sections", "outro",
            "total_duration_seconds", "tags", "description",
        ],
        "additionalProperties": False,
    },
}

TOPICS_JSON_SCHEMA: dict[str, Any] = {
    "name": "topic_suggestions",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["topics"],
        "additionalProperties": False,
    },
}


class _OpenAIClient:
    """Thin async wrapper around the OpenAI Chat Completions endpoint."""

    BASE_URL = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4o"

    MAX_RETRIES = 4
    RETRY_BACKOFF_BASE = 1.5
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, timeout: float = 120.0) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._timeout = httpx.Timeout(timeout)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4_096,
        model: str = DEFAULT_MODEL,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = await client.post(
                        self.BASE_URL,
                        headers=self._headers,
                        json=payload,
                    )

                    if resp.status_code in self.RETRY_STATUS_CODES:
                        wait = self.RETRY_BACKOFF_BASE ** attempt
                        logger.warning(
                            "OpenAI returned %s on attempt %d/%d \u2014 retrying in %.1fs",
                            resp.status_code, attempt + 1, self.MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

                except httpx.TimeoutException as exc:
                    wait = self.RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Request timed out on attempt %d/%d \u2014 retrying in %.1fs",
                        attempt + 1, self.MAX_RETRIES, wait,
                    )
                    last_exc = exc
                    await asyncio.sleep(wait)

                except httpx.HTTPStatusError as exc:
                    logger.error("Non-retryable HTTP error: %s", exc)
                    raise

        raise RuntimeError(
            f"OpenAI request failed after {self.MAX_RETRIES} attempts"
        ) from last_exc


class ScriptGenerator:
    """Generates faceless YouTube video scripts using gpt-4o via httpx."""

    def __init__(self, config) -> None:
        self._config = config
        self._client = _OpenAIClient(api_key=config.openai_api_key)

    def _target_seconds(self) -> int:
        return int(self._config.target_video_length_minutes * 60)

    def _word_range(self) -> str:
        return f"{self._config.min_script_words}\u2013{self._config.max_script_words}"

    def _style_instruction(self, style: str) -> str:
        if style not in VALID_STYLES:
            raise ValueError(
                f"Unknown style '{style}'. Valid styles: {sorted(VALID_STYLES)}"
            )
        return STYLE_INSTRUCTIONS[style]

    def _build_script_system_prompt(self, style: str) -> str:
        style_instr = self._style_instruction(style)
        target_sec = self._target_seconds()
        niche = self._config.niche
        word_range = self._word_range()

        return f"""You are an expert YouTube scriptwriter specialising in faceless,
narration-driven videos in the '{niche}' niche.

STYLE
{style_instr}

OUTPUT REQUIREMENTS
\u2022 Total narration word count: {word_range} words.
\u2022 Target video length: ~{target_sec} seconds ({self._config.target_video_length_minutes:.1f} minutes).
\u2022 Distribute that duration across the sections (each section should have a
  realistic duration_seconds).  The sum of section durations plus ~10 s for
  the hook and ~20 s for the outro should equal total_duration_seconds.

HOOK  (field: "hook")
\u2022 Maximum 2\u20133 sentences, ~5\u20138 seconds of spoken audio.
\u2022 Must create immediate curiosity or emotional tension.
\u2022 Do NOT start with "In this video\u2026" \u2014 use a provocative statement or question.

SECTIONS  (field: "sections")
\u2022 4\u20137 sections.  Each has:
    - heading        : short label (3\u20137 words)
    - narration      : full spoken narration for that section (no stage directions)
    - visual_notes   : concrete B-roll / stock-footage search terms and shot
                       suggestions for a video editor.  Use comma-separated
                       phrases.
    - duration_seconds: integer seconds of screen time for this section

OUTRO  (field: "outro")
\u2022 2\u20134 sentences.  Include a call-to-action (like, subscribe, comment question).

TAGS  (field: "tags")
\u2022 15\u201325 YouTube tags as an array of strings.
\u2022 Mix broad category tags, specific topic tags, and long-tail keyword phrases.

DESCRIPTION  (field: "description")
\u2022 150\u2013300 words.  SEO-optimised.
\u2022 First 2 sentences are the most important (appear above the fold).
\u2022 Include the main keyword naturally in the first sentence.
\u2022 End with a subscribe CTA and 3\u20135 relevant hashtags.

TITLE  (field: "title")
\u2022 50\u201370 characters.
\u2022 Curiosity gap or strong benefit.  Avoid clickbait that misleads.

Return ONLY valid JSON conforming to the provided schema.  No markdown fences,
no extra keys."""

    def _build_script_user_prompt(self, topic: str) -> str:
        return (
            f"Write a complete video script about the following topic:\n\n"
            f"TOPIC: {topic}\n\n"
            f"Niche context: {self._config.niche}"
        )

    def _build_improve_system_prompt(self) -> str:
        return (
            "You are a senior YouTube scriptwriter and editor. "
            "You will receive an existing video script as JSON and a feedback "
            "note from a producer. Rewrite the script addressing ALL the "
            "feedback points while preserving the overall structure and length. "
            "Return ONLY valid JSON conforming to the provided schema."
        )

    def _build_improve_user_prompt(self, script, feedback: str) -> str:
        script_json = json.dumps(script.to_dict(), indent=2)
        return (
            f"EXISTING SCRIPT:\n{script_json}\n\n"
            f"PRODUCER FEEDBACK:\n{feedback}\n\n"
            "Please rewrite the script to address this feedback."
        )

    def _build_topics_prompt(self, niche: str, count: int) -> str:
        return (
            f"You are a YouTube content strategist specialising in the '{niche}' niche.\n\n"
            f"Generate {count} compelling video topic ideas that:\n"
            "\u2022 Have strong search demand and curiosity-gap potential\n"
            "\u2022 Work well for narration-only (faceless) videos\n"
            "\u2022 Span a range of angles: historical, controversial, surprising,\n"
            "  how-it-works, and hidden-secrets\n"
            "\u2022 Are specific enough to make a focused 8\u201312 minute video\n\n"
            "Return ONLY valid JSON with a single key 'topics' whose value is "
            f"an array of exactly {count} topic strings.  Each topic should be "
            "a concise, punchy title-style phrase (not a full sentence)."
        )

    @staticmethod
    def _parse_script(raw_json: str) -> VideoScript:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model returned invalid JSON: {exc}\n\nRaw:\n{raw_json}") from exc

        try:
            sections = [
                ScriptSection(
                    heading=s["heading"],
                    narration=s["narration"],
                    visual_notes=s["visual_notes"],
                    duration_seconds=int(s["duration_seconds"]),
                )
                for s in data["sections"]
            ]
            return VideoScript(
                title=data["title"],
                hook=data["hook"],
                sections=sections,
                outro=data["outro"],
                total_duration_seconds=int(data["total_duration_seconds"]),
                tags=data["tags"],
                description=data["description"],
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"Model JSON missing expected field: {exc}\n\nRaw:\n{raw_json}"
            ) from exc

    # Async public API

    async def agenerate_script(self, topic: str, style: str = "documentary") -> VideoScript:
        logger.info("Generating %s script for topic: %s", style, topic)
        system_prompt = self._build_script_system_prompt(style)
        user_prompt = self._build_script_user_prompt(topic)

        raw = await self._client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SCRIPT_JSON_SCHEMA,
            },
            temperature=0.82,
            max_tokens=4_096,
        )
        script = self._parse_script(raw)
        logger.info(
            "Script generated: '%s' (%d words, %ds)",
            script.title, script.word_count(), script.total_duration_seconds,
        )
        return script

    async def agenerate_batch(self, topics: list[str], style: str = "documentary") -> list[VideoScript]:
        logger.info("Generating batch of %d scripts (style=%s)", len(topics), style)
        tasks = [self.agenerate_script(t, style) for t in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scripts: list[VideoScript] = []
        for topic, result in zip(topics, results):
            if isinstance(result, BaseException):
                logger.error("Failed to generate script for '%s': %s", topic, result)
            else:
                scripts.append(result)

        logger.info(
            "Batch complete: %d/%d scripts generated successfully",
            len(scripts), len(topics),
        )
        return scripts

    async def asuggest_topics(self, niche: str, count: int = 10) -> list[str]:
        logger.info("Suggesting %d topics for niche: %s", count, niche)
        prompt = self._build_topics_prompt(niche, count)

        raw = await self._client.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": TOPICS_JSON_SCHEMA,
            },
            temperature=0.9,
            max_tokens=1_024,
        )

        try:
            data = json.loads(raw)
            topics: list[str] = data["topics"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(
                f"Failed to parse topic suggestions: {exc}\n\nRaw:\n{raw}"
            ) from exc

        logger.info("Suggested %d topics", len(topics))
        return topics

    async def aimprove_script(self, script, feedback: str) -> VideoScript:
        logger.info("Improving script '%s' with feedback: %s", script.title, feedback[:80])
        system_prompt = self._build_improve_system_prompt()
        user_prompt = self._build_improve_user_prompt(script, feedback)

        raw = await self._client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SCRIPT_JSON_SCHEMA,
            },
            temperature=0.75,
            max_tokens=4_096,
        )
        improved = self._parse_script(raw)
        logger.info(
            "Script improved: '%s' (%d words)",
            improved.title, improved.word_count(),
        )
        return improved

    # Sync public API

    def generate_script(self, topic: str, style: str = "documentary") -> VideoScript:
        return asyncio.run(self.agenerate_script(topic, style))

    def generate_batch(self, topics: list[str], style: str = "documentary") -> list[VideoScript]:
        return asyncio.run(self.agenerate_batch(topics, style))

    def suggest_topics(self, niche: str, count: int = 10) -> list[str]:
        return asyncio.run(self.asuggest_topics(niche, count))

    def improve_script(self, script, feedback: str) -> VideoScript:
        return asyncio.run(self.aimprove_script(script, feedback))
