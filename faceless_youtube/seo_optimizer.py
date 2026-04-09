"""
faceless_youtube/seo_optimizer.py

SEO optimization module powered by OpenAI for faceless YouTube channel automation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

NICHE_POWER_WORDS: dict[str, list[str]] = {
    "space_science": ["shocking", "revealed", "discovered", "scientists", "NASA", "universe"],
    "ancient_history": ["lost", "secret", "forbidden", "hidden", "ancient", "mystery"],
    "ocean_mysteries": ["deep sea", "never seen", "terrifying", "creature", "unknown", "abyss"],
    "true_crime": ["unsolved", "dark", "twisted", "caught", "chilling", "real"],
    "psychology": ["mind tricks", "dark psychology", "manipulation", "brain", "behavior", "hidden"],
    "technology": ["future", "AI", "revolutionize", "incredible", "exposed", "breakthrough"],
    "mythology": ["forgotten gods", "ancient power", "legend", "myth", "untold", "cursed"],
    "nature_wildlife": ["rare", "never filmed", "predator", "survival", "extreme", "wild"],
}

DEFAULT_POWER_WORDS = ["shocking", "revealed", "untold", "secret", "must watch", "incredible"]

SHORT_DESCRIPTION_TEMPLATES: dict[str, str] = {
    "space_science": (
        "Scientists just revealed shocking new findings about {title} that rewrite "
        "what we know about the universe. Subscribe for deep-space discoveries every week. "
        "#Space #NASA #Astronomy #Universe #Science"
    ),
    "ancient_history": (
        "Lost to time for thousands of years, {title} is finally being uncovered and the "
        "truth is stranger than legend. Subscribe for forgotten history every week. "
        "#History #Ancient #Archaeology #Mystery #Lost"
    ),
    "ocean_mysteries": (
        "Deep beneath the waves, {title} has remained unseen until now and what scientists "
        "found is terrifying. Subscribe for ocean mysteries every week. "
        "#Ocean #DeepSea #Marine #Mysteries #Creatures"
    ),
    "true_crime": (
        "An unsolved case for decades, {title} still haunts investigators and the evidence "
        "points somewhere chilling. Subscribe for weekly true crime deep dives. "
        "#TrueCrime #Unsolved #ColdCase #Mystery #Crime"
    ),
    "psychology": (
        "Dark psychology reveals how {title} quietly rewires your mind without you noticing. "
        "Subscribe for weekly insights into hidden human behavior. "
        "#Psychology #Mind #Behavior #DarkPsychology #Brain"
    ),
    "technology": (
        "The future just arrived: {title} is quietly reshaping everything from work to war. "
        "Subscribe for breakthrough tech explained weekly. "
        "#Technology #AI #Future #Innovation #Tech"
    ),
    "mythology": (
        "Forgotten gods and ancient power: {title} hides a legend most never hear. "
        "Subscribe for untold myths decoded every week. "
        "#Mythology #Legend #Myth #Ancient #Untold"
    ),
    "nature_wildlife": (
        "Rarely filmed and rarely survived: {title} is nature at its most extreme. "
        "Subscribe for wild encounters every week. "
        "#Nature #Wildlife #Predator #Survival #Wild"
    ),
}

DEFAULT_SHORT_DESCRIPTION = (
    "{title} \u2014 the story most channels will not tell you. Subscribe for weekly deep dives. "
    "#Documentary #MustWatch #Untold #Revealed #Facts"
)


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _chat(
    api_key: str,
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    """Send a chat completion request and return the assistant message text."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(OPENAI_CHAT_URL, headers=_headers(api_key), json=payload)
        response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


class SEOOptimizer:
    """AI-powered SEO optimization for YouTube videos."""

    def __init__(self, config: Any) -> None:
        self.api_key: str = config.openai_api_key
        self.model: str = getattr(config, "seo_model", DEFAULT_MODEL)

    def optimize_title(self, title: str, niche: str) -> str:
        power_words = NICHE_POWER_WORDS.get(niche, DEFAULT_POWER_WORDS)
        power_str = ", ".join(power_words[:4])

        system_msg = (
            "You are an expert YouTube SEO copywriter specialising in faceless "
            "channels. Your titles are curiosity-driven, emotionally compelling, "
            "and always under 60 characters."
        )
        user_msg = (
            f"Rewrite this YouTube title to be more clickable for the '{niche}' niche.\n"
            f"Power words you may use (pick 1-2 at most): {power_str}\n"
            f"Rules:\n"
            f"  - Must be under 60 characters\n"
            f"  - No clickbait lies \u2014 keep it accurate\n"
            f"  - No quotes around the title in your reply\n"
            f"  - Reply with ONLY the optimized title, nothing else\n\n"
            f"Original title: {title}"
        )

        try:
            result = _chat(
                self.api_key,
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                model=self.model,
                max_tokens=80,
                temperature=0.8,
            )
            result = result.strip('"\'').strip()
            if len(result) <= 60:
                return result
            return result[:57].rsplit(" ", 1)[0] + "..."
        except Exception as exc:
            logger.warning("OpenAI title optimisation failed (%s), using rule-based fallback.", exc)
            return self._rule_based_title(title, power_words)

    def _rule_based_title(self, title: str, power_words: list[str]) -> str:
        title = title.strip()
        title = title.title()
        for word in power_words:
            candidate = f"{word.title()}: {title}"
            if len(candidate) <= 60:
                return candidate
        return title[:57] + "..." if len(title) > 60 else title

    def optimize_description(
        self,
        description: str,
        keywords: list[str],
        channel_links: dict[str, str] | None = None,
    ) -> str:
        kw_str = ", ".join(keywords[:15])
        system_msg = (
            "You are a YouTube SEO specialist. You write descriptions that rank "
            "well in YouTube search while being genuinely useful to viewers."
        )
        user_msg = (
            "Rewrite the following YouTube video description to be SEO-optimised.\n\n"
            "Requirements:\n"
            "  1. Start with a compelling 2-sentence hook (no filler).\n"
            "  2. Include a 'Timestamps' section with at least 4 placeholder timestamps "
            "     like '00:00 - Introduction'.\n"
            "  3. Naturally include these keywords: " + kw_str + "\n"
            "  4. End with a call-to-action (Like, Comment, Subscribe).\n"
            "  5. Keep total length between 200 and 500 words.\n"
            "  6. Do NOT add any links \u2014 they will be appended separately.\n\n"
            "Original description:\n" + description
        )

        try:
            optimized = _chat(
                self.api_key,
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                model=self.model,
                max_tokens=700,
                temperature=0.6,
            )
        except Exception as exc:
            logger.warning("OpenAI description optimisation failed (%s), using original.", exc)
            optimized = description

        if channel_links:
            link_lines = ["\n\n--- Connect with us ---"]
            for label, url in channel_links.items():
                link_lines.append(f"{label}: {url}")
            optimized += "\n".join(link_lines)

        return optimized

    def build_short_description(self, title: str, niche: str) -> str:
        template = SHORT_DESCRIPTION_TEMPLATES.get(niche, DEFAULT_SHORT_DESCRIPTION)
        return template.format(title=title.strip())

    def generate_tags(
        self,
        title: str,
        description: str,
        niche: str,
        max_tags: int = 30,
    ) -> list[str]:
        system_msg = "You are a YouTube SEO expert. Generate highly relevant tags."
        user_msg = (
            f"Generate up to {max_tags} YouTube tags for the following video.\n"
            f"Niche: {niche}\n"
            f"Title: {title}\n"
            f"Description excerpt: {description[:300]}\n\n"
            "Rules:\n"
            "  - Mix short-tail (1-2 words) and long-tail (3-5 words) tags\n"
            "  - Include niche-specific terms\n"
            "  - No special characters except hyphens\n"
            "  - Return ONLY a JSON array of strings, nothing else\n"
        )

        try:
            raw = _chat(
                self.api_key,
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                model=self.model,
                max_tokens=400,
                temperature=0.5,
            )
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                tags: list[str] = json.loads(match.group())
                return [str(t).strip() for t in tags[:max_tags]]
        except Exception as exc:
            logger.warning("OpenAI tag generation failed (%s), using keyword-based fallback.", exc)

        return self._keyword_tags(title, niche, max_tags)

    def _keyword_tags(self, title: str, niche: str, max_tags: int) -> list[str]:
        words = re.findall(r"[a-zA-Z]{3,}", title)
        tags = list(dict.fromkeys(words))
        tags += NICHE_POWER_WORDS.get(niche, DEFAULT_POWER_WORDS)
        tags.append(niche.replace("_", " "))
        return tags[:max_tags]

    def generate_hashtags(self, tags: list[str], max: int = 3) -> list[str]:
        if not tags:
            return []
        candidates = sorted(tags, key=lambda t: len(t.split()), reverse=True)
        hashtags: list[str] = []
        seen: set[str] = set()
        for tag in candidates:
            slug = re.sub(r"[^a-zA-Z0-9]", "", tag.title().replace(" ", ""))
            if slug and slug.lower() not in seen:
                hashtags.append(f"#{slug}")
                seen.add(slug.lower())
            if len(hashtags) >= max:
                break
        return hashtags

    def analyze_competition(self, topic: str) -> dict[str, Any]:
        system_msg = (
            "You are a YouTube SEO analyst. Estimate keyword competition based on "
            "your knowledge of typical YouTube content saturation."
        )
        user_msg = (
            f"Analyse the YouTube keyword competition for the topic: '{topic}'\n\n"
            "Return a JSON object with these exact keys:\n"
            "  difficulty_score: integer 1-100 (100 = hardest)\n"
            "  competition_level: one of 'low', 'medium', 'high'\n"
            "  estimated_monthly_searches: string like '10K-50K'\n"
            "  suggested_angle: string \u2014 a unique angle to stand out\n"
            "  related_low_competition_keywords: list of 5 strings\n\n"
            "Return ONLY the JSON object, no markdown fences."
        )

        try:
            raw = _chat(
                self.api_key,
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                model=self.model,
                max_tokens=400,
                temperature=0.4,
            )
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Competition analysis failed (%s), returning defaults.", exc)
            return {
                "difficulty_score": 50,
                "competition_level": "medium",
                "estimated_monthly_searches": "Unknown",
                "suggested_angle": "Focus on a unique, underserved perspective.",
                "related_low_competition_keywords": [],
            }

    def suggest_related_keywords(self, seed_keyword: str, count: int = 10) -> list[str]:
        system_msg = "You are a YouTube keyword researcher."
        user_msg = (
            f"Generate {count} related YouTube search keywords for: '{seed_keyword}'\n"
            "Focus on mid-tail keywords (2-4 words) with good search intent.\n"
            "Return ONLY a JSON array of strings."
        )
        try:
            raw = _chat(
                self.api_key,
                [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                model=self.model,
                max_tokens=300,
                temperature=0.6,
            )
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group())[:count]
        except Exception as exc:
            logger.warning("Keyword suggestion failed: %s", exc)
        return []

    def build_full_metadata(
        self,
        title: str,
        description: str,
        tags: list[str],
        niche: str,
    ) -> dict[str, Any]:
        logger.info("Building full SEO metadata for '%s'", title)

        raw_keywords: list[str] = tags[:] + re.findall(r"[a-zA-Z]{4,}", title)
        raw_keywords = list(dict.fromkeys(raw_keywords))[:20]

        optimized_title = self.optimize_title(title, niche)
        optimized_tags = self.generate_tags(optimized_title, description, niche)
        optimized_description = self.optimize_description(description, raw_keywords)
        hashtags = self.generate_hashtags(optimized_tags)
        keyword_analysis = self.analyze_competition(optimized_title)
        related_keywords = self.suggest_related_keywords(optimized_title, count=8)

        return {
            "optimized_title": optimized_title,
            "optimized_description": optimized_description,
            "optimized_tags": optimized_tags,
            "hashtags": hashtags,
            "keyword_analysis": keyword_analysis,
            "related_keywords": related_keywords,
        }
