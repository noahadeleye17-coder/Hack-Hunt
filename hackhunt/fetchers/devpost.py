"""Devpost source: the unofficial JSON listing plus each hackathon's page for
the exact deadline and eligibility (the listing has neither)."""

import html
import logging
import re
import time
from datetime import date, datetime

import requests

from ..models import Hackathon

log = logging.getLogger(__name__)

SOURCE = "devpost"
LIST_URL = "https://devpost.com/api/hackathons"
USER_AGENT = "Mozilla/5.0 (compatible; hackhunt/0.1; daily hackathon digest)"
TIMEOUT = 20
MAX_PAGES = 40

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_TAG = re.compile(r"<[^>]+>")
_PERIOD_PART = re.compile(r"^(?:([A-Za-z]{3})[a-z]*\.?\s+)?(\d{1,2})(?:,\s*(\d{4}))?$")
_ONLINE = re.compile(r"\b(online|virtual)\b", re.I)
_USD = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_DEADLINE = re.compile(r'class="deadline[^"]*"[^>]*?data-iso-date="([^"]+)"')
_ELIGIBILITY = re.compile(r'<ul id="eligibility-list"[^>]*>(.*?)</ul>', re.S)
_COUNTRIES_TITLE = re.compile(r'id="eligibility-countries-modal-title"[^>]*>(.*?)</h4>', re.S)
_COUNTRIES_LIST = re.compile(r'<ul id="eligibility-countries-modal-list"[^>]*>(.*?)</ul>', re.S)
_LI = re.compile(r"<li[^>]*>(.*?)</li>", re.S)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def fetch_listing(session: requests.Session, delay: float) -> tuple[list[Hackathon], list[str]]:
    """All open hackathons. Never raises; problems come back as error strings."""
    hackathons: dict[str, Hackathon] = {}
    errors: list[str] = []
    for page in range(1, MAX_PAGES + 1):
        if page > 1:
            time.sleep(delay)
        try:
            r = session.get(LIST_URL, params={"status[]": "open", "page": page}, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            errors.append(f"Devpost listing page {page} failed: {e}")
            break
        items = data.get("hackathons") or []
        if not items:
            break
        for raw in items:
            try:
                h = parse_listing_item(raw)
            except (KeyError, TypeError, ValueError) as e:
                errors.append(f"Devpost: couldn't parse hackathon {raw.get('id')!r}: {e}")
                continue
            hackathons.setdefault(h.id, h)
        total = (data.get("meta") or {}).get("total_count")
        if isinstance(total, int) and len(hackathons) >= total:
            break
    else:
        errors.append(f"Devpost listing stopped at the {MAX_PAGES}-page limit")
    return list(hackathons.values()), errors


def fetch_details(session: requests.Session, h: Hackathon) -> str | None:
    """Fill in deadline and eligibility from the hackathon page. Returns an error or None."""
    try:
        r = session.get(h.url, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        return f"Devpost: couldn't load the page for {h.title} ({_short(e)}), will retry next run"
    if not parse_detail(r.text, h):
        return f"Devpost: page layout not recognised for {h.title} (no deadline or eligibility found)"
    return None


def _short(e: requests.RequestException) -> str:
    status = getattr(e.response, "status_code", None)
    return f"HTTP {status}" if status else type(e).__name__


def parse_listing_item(raw: dict) -> Hackathon:
    loc = raw.get("displayed_location") or {}
    location = loc.get("location") or ""
    start, end = parse_period(raw.get("submission_period_dates") or "")
    prize_text = clean(raw.get("prize_amount"), tag_sep="")  # "$<span>100,000</span>"
    return Hackathon(
        id=f"devpost:{raw['id']}",
        source=SOURCE,
        title=clean(raw["title"]),
        url=raw["url"],
        organizer=raw.get("organization_name") or "",
        start_date=start,
        end_date=end,
        # Also catches "virtual" and hybrid listings like "Bay Area + Online".
        online=loc.get("icon") == "globe" or _ONLINE.search(location) is not None,
        location=location,
        prize_usd=parse_usd(prize_text),
        prize_text=prize_text,
        themes=[t["name"] for t in raw.get("themes") or []],
        registrations=raw.get("registrations_count"),
        invite_only=bool(raw.get("invite_only")),
    )


def parse_detail(page: str, h: Hackathon) -> bool:
    """Returns False if none of the expected blocks were found."""
    found = False
    m = _DEADLINE.search(page)
    if m:
        try:
            dt = datetime.fromisoformat(m.group(1))
        except ValueError:
            dt = None
        if dt is not None and dt.tzinfo is not None:
            h.deadline = dt
            found = True
    m = _ELIGIBILITY.search(page)
    if m:
        h.eligibility = [t for t in (clean(li) for li in _LI.findall(m.group(1))) if t]
        found = True
    title, items = _COUNTRIES_TITLE.search(page), _COUNTRIES_LIST.search(page)
    if title and items:
        title_text = clean(title.group(1)).lower()
        if "excluded" in title_text:
            h.countries_mode = "excluded"
        elif "included" in title_text:
            h.countries_mode = "included"
        if h.countries_mode:
            h.countries = [t for t in (clean(li) for li in _LI.findall(items.group(1))) if t]
    return found


def parse_period(text: str) -> tuple[date | None, date | None]:
    """'Oct 30 - Dec 04, 2026', 'Nov 11 - 30, 2026', 'Nov 11, 2026 - Jan 11, 2027'."""
    parts = []
    for p in text.split(" - "):
        m = _PERIOD_PART.match(p.strip())
        if not m:
            return None, None
        parts.append(m.groups())
    if len(parts) == 1:
        parts *= 2
    if len(parts) != 2:
        return None, None
    (l_mon, l_day, l_year), (r_mon, r_day, r_year) = parts
    if l_mon is None or r_year is None:
        return None, None
    try:
        end = date(int(r_year), _MONTHS[(r_mon or l_mon).lower()], int(r_day))
        start = date(int(l_year or r_year), _MONTHS[l_mon.lower()], int(l_day))
        if l_year is None and start > end:
            start = start.replace(year=end.year - 1)
    except (KeyError, ValueError):
        return None, None
    return start, end


def parse_usd(text: str) -> float | None:
    m = _USD.fullmatch(text.strip())
    return float(m.group(1).replace(",", "")) if m else None


def clean(fragment: str | None, tag_sep: str = " ") -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(tag_sep, fragment or ""))).strip()
