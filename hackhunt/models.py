from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

# Nigeria has no daylight saving, so a fixed UTC+1 offset is exact
# and avoids needing the tzdata package on Windows.
LAGOS = timezone(timedelta(hours=1), "WAT")


def today_lagos(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(LAGOS).date()


@dataclass
class Hackathon:
    id: str
    source: str
    title: str
    url: str
    organizer: str = ""
    start_date: date | None = None
    end_date: date | None = None  # last day of the submission period, from the listing
    deadline: datetime | None = None  # exact, timezone-aware, from the hackathon page
    online: bool = False
    location: str = ""
    prize_usd: float | None = None  # None when the prize isn't in USD
    prize_text: str = ""
    themes: list[str] = field(default_factory=list)
    eligibility: list[str] = field(default_factory=list)
    countries_mode: str = ""  # "included", "excluded" or "" if no country list
    countries: list[str] = field(default_factory=list)
    registrations: int | None = None
    invite_only: bool = False
    first_seen: str = ""
    score: float = 0.0
    score_breakdown: dict[str, tuple[float, str]] = field(default_factory=dict)
    score_reason: str = ""

    def deadline_date(self) -> date | None:
        """Deadline as a calendar date in Lagos time."""
        if self.deadline is not None:
            return self.deadline.astimezone(LAGOS).date()
        return self.end_date

    def days_left(self, today: date) -> int | None:
        d = self.deadline_date()
        return None if d is None else (d - today).days
