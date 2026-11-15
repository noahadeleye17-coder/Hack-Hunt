"""Hard rules. Each check returns a reason string when a hackathon should be dropped."""

from datetime import date

from .config import Settings
from .models import Hackathon


def basic_drop_reason(h: Hackathon, settings: Settings, today: date) -> str | None:
    if settings.online_only and not h.online:
        return f"not online ({h.location or 'no location'})"
    if h.invite_only:
        return "invite only"
    days = h.days_left(today)
    if days is None:
        return "no deadline found"
    if days < settings.min_days_left:
        return f"only {days} days left (minimum {settings.min_days_left})"
    return None


def eligibility_drop_reason(h: Hackathon, settings: Settings) -> str | None:
    home = settings.country.lower()
    countries = {c.lower() for c in h.countries}
    if h.countries_mode == "excluded" and home in countries:
        return f"{settings.country} is on the excluded countries list"
    if h.countries_mode == "included" and countries and home not in countries:
        return f"{settings.country} isn't on the allowed countries list"
    text = " ".join(h.eligibility).lower()
    for phrase in settings.exclude_phrases:
        if phrase.lower() in text:
            return f'eligibility says "{phrase}"'
    return None


def reminder_due(h: Hackathon, entry: dict, today: date, urgent_days: int) -> bool:
    """An already-digested hackathon gets one 'closing soon' reminder."""
    if entry.get("status") != "digested" or entry.get("urgent_flagged_at"):
        return False
    days = h.days_left(today)
    return days is not None and 0 <= days <= urgent_days
