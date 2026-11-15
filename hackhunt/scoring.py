"""Rule-based fit score. Every part keeps a short reason so the digest can explain the rank."""

import math
import re
from datetime import date

from .models import Hackathon

INTEREST_POINTS = 10
INTEREST_CAP = 30
PRIZE_POINTS_PER_TENFOLD = 4  # $1k -> 12, $10k -> 16, $100k -> 20
PRIZE_CAP = 24
SWEET_SPOT_DAYS = (7, 30)


def score(h: Hackathon, interests: dict[str, list[str]], today: date) -> None:
    parts = {
        "interests": interest_points(h, interests),
        "prize": prize_points(h),
        "time": time_points(h.days_left(today)),
        "registrations": registration_points(h.registrations),
    }
    h.score_breakdown = parts
    h.score = round(sum(p for p, _ in parts.values()), 1)
    h.score_reason = " · ".join(why for _, why in parts.values() if why)


def interest_points(h: Hackathon, interests: dict[str, list[str]]) -> tuple[float, str]:
    text = " | ".join([h.title, *h.themes]).lower()
    matched = [name for name, keywords in interests.items() if any(_has_word(k, text) for k in keywords)]
    if not matched:
        return 0.0, "no interest match"
    return float(min(len(matched) * INTEREST_POINTS, INTEREST_CAP)), "matches " + ", ".join(matched)


def prize_points(h: Hackathon) -> tuple[float, str]:
    if h.prize_usd is None:
        return 0.0, f"prize {h.prize_text or 'unknown'} (not USD, not scored)"
    if h.prize_usd == 0:
        return 0.0, "no cash prize"
    pts = min(PRIZE_CAP, PRIZE_POINTS_PER_TENFOLD * math.log10(h.prize_usd + 1))
    return round(pts, 1), f"${h.prize_usd:,.0f} prize"


def time_points(days: int | None) -> tuple[float, str]:
    if days is None:
        return 0.0, "deadline unknown"
    low, high = SWEET_SPOT_DAYS
    if low <= days <= high:
        pts = 15.0
    elif days < low:
        pts = 8.0
    elif days <= 60:
        pts = 10.0
    else:
        pts = 5.0
    return pts, f"{days} days left"


def registration_points(count: int | None) -> tuple[float, str]:
    if count is None:
        return 0.0, ""
    if count < 200:
        pts = 5.0
    elif count < 1000:
        pts = 3.0
    elif count < 5000:
        pts = 1.0
    else:
        pts = 0.0
    return pts, f"{count:,} registered"


def _has_word(keyword: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])", text) is not None
