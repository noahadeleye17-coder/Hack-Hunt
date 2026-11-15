"""Seen hackathons, kept in a small JSON file the workflow commits back."""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import Hackathon

KEEP_DAYS_AFTER_DEADLINE = 30


class SeenStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        # Refuse to continue on a bad file rather than resend everything.
        if not isinstance(data, dict):
            raise ValueError(f"{self.path} should contain a JSON object")
        return data

    def get(self, hackathon_id: str) -> dict | None:
        return self.entries.get(hackathon_id)

    @staticmethod
    def restore(h: Hackathon, entry: dict) -> None:
        """Put back what the listing doesn't carry (the exact deadline)."""
        h.first_seen = entry.get("first_seen", "")
        if entry.get("deadline"):
            h.deadline = datetime.fromisoformat(entry["deadline"])

    def mark_digested(self, h: Hackathon, now: datetime) -> None:
        entry = self._upsert(h, now, "digested")
        entry["digested_at"] = now.isoformat(timespec="seconds")
        entry["score"] = h.score
        entry["score_breakdown"] = {k: list(v) for k, v in h.score_breakdown.items()}

    def mark_dropped(self, h: Hackathon, reason: str, now: datetime) -> None:
        self._upsert(h, now, "dropped")["reason"] = reason

    def mark_urgent(self, hackathon_id: str, now: datetime) -> None:
        self.entries[hackathon_id]["urgent_flagged_at"] = now.isoformat(timespec="seconds")

    def prune(self, today: date) -> None:
        cutoff = (today - timedelta(days=KEEP_DAYS_AFTER_DEADLINE)).isoformat()
        self.entries = {k: v for k, v in self.entries.items() if (v.get("end_date") or "9999") >= cutoff}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(self.entries, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, self.path)

    def _upsert(self, h: Hackathon, now: datetime, status: str) -> dict:
        entry = self.entries.setdefault(h.id, {"first_seen": h.first_seen or now.isoformat(timespec="seconds")})
        deadline_date = h.deadline_date()
        entry.update(
            title=h.title,
            url=h.url,
            status=status,
            deadline=h.deadline.isoformat() if h.deadline else None,
            end_date=deadline_date.isoformat() if deadline_date else None,
        )
        return entry
