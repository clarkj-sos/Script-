"""Pre-built niche configurations for faceless YouTube channels."""
from __future__ import annotations
import random
from typing import Dict, List, Optional


NICHES: Dict[str, dict] = {
    "space_science": {
        "name": "Space & Science",
        "description": "Cosmos, astrophysics, NASA missions, mysteries of the universe",
        "default_style": "documentary",
        "thumbnail_preset": 1,
        "target_audience": "Science enthusiasts, ages 18-45",
        "optimal_video_length_minutes": 12,
        "default_tags": ["space", "science", "astronomy", "nasa", "universe", "documentary"],
        "suggested_topics": [
            "What's actually inside a black hole",
            "The terrifying truth about the dark side of the Moon",
            "How the James Webb telescope is rewriting physics",
            "The asteroid that could end humanity",
            "Why time slows down near a black hole",
            "What happens if you fall into Jupiter",
            "The mystery of dark matter explained",
            "How NASA plans to colonize Mars",
            "The strangest planets ever discovered",
            "What existed before the Big Bang",
        ],
    },
    "ancient_history": {
        "name": "Ancient History",
        "description": "Lost civilizations, archaeology, ancient mysteries",
        "default_style": "storytelling",
        "thumbnail_preset": 4,
        "target_audience": "History buffs, ages 25-55",
        "optimal_video_length_minutes": 15,
        "default_tags": ["history", "ancient", "archaeology", "civilization", "mystery"],
        "suggested_topics": [
            "The lost city of Atlantis: real evidence",
            "How the pyramids were actually built",
            "The Antikythera mechanism: ancient computer",
            "Forbidden archaeology they don't teach you",
            "The Bronze Age collapse mystery",
            "G\u00f6bekli Tepe: 12,000-year-old temple",
            "The truth about the Roman Empire's fall",
            "Lost technologies of ancient Egypt",
            "The Indus Valley: history's silent giant",
            "Who really built Stonehenge",
        ],
    },
    "ocean_mysteries": {
        "name": "Ocean Mysteries",
        "description": "Deep sea, marine biology, underwater discoveries",
        "default_style": "mystery",
        "thumbnail_preset": 2,
        "target_audience": "Curious minds, ages 16-40",
        "optimal_video_length_minutes": 10,
        "default_tags": ["ocean", "deep sea", "marine", "mysteries", "creatures"],
        "suggested_topics": [
            "Creatures found in the Mariana Trench",
            "The lost city beneath the Black Sea",
            "Why we know more about Mars than our oceans",
            "The Bloop and other unexplained ocean sounds",
            "Megalodon: could it still exist?",
            "The Bermuda Triangle: science vs myth",
            "Underwater rivers that defy physics",
            "The Sargasso Sea: ocean within an ocean",
            "Ghost ships found drifting in 2024",
            "The deepest place on Earth explained",
        ],
    },
    "true_crime": {
        "name": "True Crime",
        "description": "Cold cases, unsolved mysteries, criminal psychology",
        "default_style": "storytelling",
        "thumbnail_preset": 3,
        "target_audience": "True crime fans, ages 25-55",
        "optimal_video_length_minutes": 20,
        "default_tags": ["true crime", "mystery", "unsolved", "cold case", "investigation"],
        "suggested_topics": [
            "The Zodiac killer: new evidence",
            "DB Cooper: where did he land?",
            "The Dyatlov Pass mystery solved?",
            "JonBen\u00e9t Ramsey: 28 years later",
            "The Black Dahlia: what we now know",
            "The Long Island serial killer arrest",
            "Tara Calico: the photo that haunts everyone",
            "The vanishing of Madeleine McCann",
            "The Boy in the Box finally identified",
            "The Sodder children mystery",
        ],
    },
    "psychology": {
        "name": "Psychology & Mind",
        "description": "Human behavior, cognitive biases, mental phenomena",
        "default_style": "explainer",
        "thumbnail_preset": 6,
        "target_audience": "Self-improvement, ages 18-45",
        "optimal_video_length_minutes": 8,
        "default_tags": ["psychology", "mind", "behavior", "self improvement", "mental health"],
        "suggested_topics": [
            "10 psychological tricks that actually work",
            "Why your brain lies to you",
            "The dark psychology of manipulators",
            "How trauma reshapes your brain",
            "The Dunning-Kruger effect explained",
            "Why nostalgia hurts and helps",
            "The science of falling in love",
            "How to spot a narcissist in 5 minutes",
            "Why we believe in conspiracy theories",
            "The psychology of fear and how to beat it",
        ],
    },
    "technology": {
        "name": "Technology & Future",
        "description": "AI, future tech, breakthroughs, sci-tech explainers",
        "default_style": "explainer",
        "thumbnail_preset": 6,
        "target_audience": "Tech enthusiasts, ages 18-45",
        "optimal_video_length_minutes": 10,
        "default_tags": ["technology", "AI", "future", "innovation", "science"],
        "suggested_topics": [
            "How AI will change everything in 5 years",
            "Quantum computers explained simply",
            "Neuralink: the truth about brain chips",
            "Self-driving cars: why they keep failing",
            "The race to build a fusion reactor",
            "Inside China's AI arms race",
            "How TikTok actually knows what you want",
            "The internet's hidden infrastructure",
            "Robots that learn like humans",
            "The end of passwords explained",
        ],
    },
    "mythology": {
        "name": "Mythology & Folklore",
        "description": "Ancient gods, monsters, legends across cultures",
        "default_style": "storytelling",
        "thumbnail_preset": 5,
        "target_audience": "Mythology fans, ages 16-45",
        "optimal_video_length_minutes": 12,
        "default_tags": ["mythology", "legends", "folklore", "gods", "monsters"],
        "suggested_topics": [
            "The most terrifying creatures in Norse myth",
            "Greek gods you've never heard of",
            "Japanese yokai that still scare people",
            "The real Cthulhu: cosmic horror origins",
            "Slavic mythology: forgotten and dark",
            "Hindu creation: the cosmic ocean",
            "Celtic gods of the underworld",
            "The Wendigo: native American horror",
            "Egyptian afterlife: the 42 judges",
            "Mesopotamian myths older than the Bible",
        ],
    },
    "nature_wildlife": {
        "name": "Nature & Wildlife",
        "description": "Animals, ecosystems, evolution, natural wonders",
        "default_style": "documentary",
        "thumbnail_preset": 1,
        "target_audience": "Nature lovers, ages 12-65",
        "optimal_video_length_minutes": 12,
        "default_tags": ["nature", "wildlife", "animals", "documentary", "biology"],
        "suggested_topics": [
            "The deadliest animals you've never heard of",
            "Inside the immortal jellyfish",
            "How octopuses are basically aliens",
            "Animals that came back from extinction",
            "The deep sea's strangest creatures",
            "Why elephants never forget",
            "The wolves that changed Yellowstone",
            "Birds that solve puzzles better than kids",
            "The truth about apex predators",
            "Insects with superpowers",
        ],
    },
}


class NicheLibrary:
    def __init__(self, config=None) -> None:
        self.config = config

    def get_niche(self, name: str) -> dict:
        if name not in NICHES:
            raise KeyError(f"Unknown niche: {name}. Available: {list(NICHES.keys())}")
        return NICHES[name]

    def list_niches(self) -> List[str]:
        return list(NICHES.keys())

    def get_topics(self, niche: str) -> List[str]:
        return list(self.get_niche(niche)["suggested_topics"])

    def get_random_topic(self, niche: str) -> str:
        return random.choice(self.get_topics(niche))

    def suggest_trending_topics(self, niche: str, count: int = 5) -> List[str]:
        """Returns a sample from suggested_topics. For LLM-powered trending, use ScriptGenerator.suggest_topics."""
        topics = self.get_topics(niche)
        return random.sample(topics, min(count, len(topics)))
