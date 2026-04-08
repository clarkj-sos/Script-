"""Analytics tracker for video performance."""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class AnalyticsTracker:
    def __init__(self, config) -> None:
        self.config = config
        self.path = Path(config.output_dir) / "analytics.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def record_upload(self, video_id: str, title: str, topic: str, niche: str,
                       uploaded_at: Optional[datetime] = None, metadata: Optional[dict] = None) -> None:
        self.data[video_id] = {
            "video_id": video_id,
            "title": title,
            "topic": topic,
            "niche": niche,
            "uploaded_at": (uploaded_at or datetime.now()).isoformat(),
            "metadata": metadata or {},
            "performance": {"views": 0, "likes": 0, "comments": 0, "watch_time_hours": 0},
        }
        self.save()

    def record_performance(self, video_id: str, views: int, likes: int,
                            comments: int, watch_time_hours: float = 0) -> None:
        if video_id not in self.data:
            return
        self.data[video_id]["performance"] = {
            "views": views, "likes": likes, "comments": comments,
            "watch_time_hours": watch_time_hours,
            "engagement_rate": round((likes + comments) / views * 100, 2) if views > 0 else 0,
            "last_updated": datetime.now().isoformat(),
        }
        self.save()

    def get_best_performing(self, metric: str = "views", top_n: int = 5) -> List[dict]:
        items = list(self.data.values())
        items.sort(key=lambda x: x.get("performance", {}).get(metric, 0), reverse=True)
        return items[:top_n]

    def get_niche_performance(self, niche: str) -> dict:
        items = [v for v in self.data.values() if v.get("niche") == niche]
        if not items:
            return {"niche": niche, "video_count": 0}
        total_views = sum(v["performance"]["views"] for v in items)
        total_eng = sum(v["performance"].get("engagement_rate", 0) for v in items)
        return {
            "niche": niche,
            "video_count": len(items),
            "total_views": total_views,
            "avg_views": total_views // len(items),
            "avg_engagement_rate": round(total_eng / len(items), 2),
        }

    def get_upload_history(self, days: int = 30) -> List[dict]:
        cutoff = datetime.now() - timedelta(days=days)
        results = []
        for v in self.data.values():
            try:
                if datetime.fromisoformat(v["uploaded_at"]) >= cutoff:
                    results.append(v)
            except (KeyError, ValueError):
                continue
        return sorted(results, key=lambda x: x["uploaded_at"], reverse=True)

    def suggest_improvements(self) -> List[str]:
        suggestions = []
        if not self.data:
            return ["No data yet \u2014 upload videos first"]
        avg_views = sum(v["performance"]["views"] for v in self.data.values()) / len(self.data)
        underperformers = [v for v in self.data.values() if v["performance"]["views"] < avg_views * 0.5]
        if underperformers:
            suggestions.append(f"{len(underperformers)} videos performing below 50% of average \u2014 review thumbnails/titles")
        avg_eng = sum(v["performance"].get("engagement_rate", 0) for v in self.data.values()) / len(self.data)
        if avg_eng < 2.0:
            suggestions.append(f"Engagement rate low ({avg_eng:.1f}%) \u2014 add stronger CTAs and questions")
        if len(self.data) < 10:
            suggestions.append("Upload consistency matters \u2014 aim for at least 10 videos before judging performance")
        return suggestions or ["Performance looks healthy \u2014 keep going"]

    def generate_report(self) -> str:
        lines = ["# Analytics Report", f"Generated: {datetime.now().isoformat()}", ""]
        lines.append(f"**Total videos tracked**: {len(self.data)}")
        if not self.data:
            return "\n".join(lines)
        total_views = sum(v["performance"]["views"] for v in self.data.values())
        lines.append(f"**Total views**: {total_views:,}")
        lines.append("\n## Top 5 by Views\n")
        for i, v in enumerate(self.get_best_performing("views", 5), 1):
            lines.append(f"{i}. **{v['title']}** \u2014 {v['performance']['views']:,} views")
        lines.append("\n## Suggestions\n")
        for s in self.suggest_improvements():
            lines.append(f"- {s}")
        return "\n".join(lines)
