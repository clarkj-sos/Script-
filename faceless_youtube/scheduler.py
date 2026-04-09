"""Content scheduler and queue manager."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


WEEKDAY_INDEX = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}


@dataclass
class ScheduledVideo:
    topic: str
    scheduled_date: str  # ISO 8601
    status: str = "pending"  # pending|generating|uploading|published|failed
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    video_id: Optional[str] = None


class ContentScheduler:
    def __init__(self, config) -> None:
        self.config = config
        self.schedule_file = Path(config.output_dir) / "schedule.json"
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        self.schedule: List[ScheduledVideo] = []
        self.load()

    # persistence
    def load(self) -> None:
        if self.schedule_file.exists():
            data = json.loads(self.schedule_file.read_text(encoding="utf-8"))
            self.schedule = [ScheduledVideo(**item) for item in data]

    def save(self) -> None:
        data = [asdict(s) for s in self.schedule]
        self.schedule_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # queue ops
    def add_to_queue(self, topic: str, scheduled_date: Optional[datetime] = None) -> ScheduledVideo:
        when = scheduled_date or self._next_upload_slot()
        sv = ScheduledVideo(topic=topic, scheduled_date=when.isoformat())
        self.schedule.append(sv)
        self.save()
        return sv

    def remove_from_queue(self, topic: str) -> None:
        self.schedule = [s for s in self.schedule if s.topic != topic]
        self.save()

    def get_next(self) -> Optional[ScheduledVideo]:
        pending = [s for s in self.schedule if s.status == "pending"]
        if not pending:
            return None
        pending.sort(key=lambda s: s.scheduled_date)
        return pending[0]

    def get_schedule(self) -> List[ScheduledVideo]:
        return list(self.schedule)

    def auto_schedule(self, topics: List[str]) -> List[ScheduledVideo]:
        """Spread topics across upcoming upload slots."""
        results = []
        slot = self._next_upload_slot()
        for topic in topics:
            sv = ScheduledVideo(topic=topic, scheduled_date=slot.isoformat())
            self.schedule.append(sv)
            results.append(sv)
            slot = self._advance_slot(slot)
        self.save()
        return results

    def update_status(self, topic: str, status: str, **kwargs) -> None:
        for s in self.schedule:
            if s.topic == topic:
                s.status = status
                for k, v in kwargs.items():
                    if hasattr(s, k):
                        setattr(s, k, v)
        self.save()

    def run_due(self) -> List[ScheduledVideo]:
        now = datetime.now()
        due = []
        for s in self.schedule:
            if s.status == "pending":
                try:
                    sched = datetime.fromisoformat(s.scheduled_date)
                    if sched <= now:
                        due.append(s)
                except ValueError:
                    continue
        return due

    # slot calculation
    def _next_upload_slot(self, after: Optional[datetime] = None) -> datetime:
        after = after or datetime.now()
        upload_days = [WEEKDAY_INDEX[d] for d in self.config.upload_days if d in WEEKDAY_INDEX]
        if not upload_days:
            return after + timedelta(days=1)
        hour, minute = map(int, self.config.upload_time.split(":"))
        for offset in range(0, 14):
            candidate = after + timedelta(days=offset)
            if candidate.weekday() in upload_days:
                slot = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if slot > after:
                    return slot
        return after + timedelta(days=1)

    def _advance_slot(self, current: datetime) -> datetime:
        return self._next_upload_slot(after=current + timedelta(minutes=1))
