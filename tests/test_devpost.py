import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hackhunt.fetchers.devpost import parse_detail, parse_listing_item, parse_period, parse_usd
from hackhunt.models import today_lagos

from .helpers import make

FIXTURES = Path(__file__).parent / "fixtures"


class ListingTest(unittest.TestCase):
    def test_parses_saved_response(self):
        raw = json.loads((FIXTURES / "devpost_page1.json").read_text(encoding="utf-8"))
        items = [parse_listing_item(r) for r in raw["hackathons"]]
        self.assertEqual(len(items), len(raw["hackathons"]))
        first = items[0]
        self.assertEqual(first.id, "devpost:31667")
        self.assertEqual(first.title, "Kiroween 2026")
        self.assertTrue(first.online)
        self.assertEqual(first.prize_usd, 100000)
        self.assertEqual(first.prize_text, "$100,000")
        self.assertEqual(first.end_date, date(2026, 12, 4))
        self.assertIn("Machine Learning/AI", first.themes)
        self.assertTrue(all(h.end_date for h in items))

    def test_period_formats(self):
        self.assertEqual(parse_period("Oct 30 - Dec 04, 2026"), (date(2026, 10, 30), date(2026, 12, 4)))
        self.assertEqual(parse_period("Nov 11 - 30, 2026"), (date(2026, 11, 11), date(2026, 11, 30)))
        self.assertEqual(parse_period("Nov 11, 2026 - Jan 11, 2027"), (date(2026, 11, 11), date(2027, 1, 11)))
        self.assertEqual(parse_period("Dec 20 - Jan 05, 2027"), (date(2026, 12, 20), date(2027, 1, 5)))
        self.assertEqual(parse_period("whenever"), (None, None))

    def test_usd_only(self):
        self.assertEqual(parse_usd("$1,500"), 1500)
        self.assertEqual(parse_usd("$0"), 0)
        self.assertIsNone(parse_usd("€5,000"))
        self.assertIsNone(parse_usd("₹50,000"))
        self.assertIsNone(parse_usd(""))


class DetailTest(unittest.TestCase):
    def test_parses_saved_page(self):
        h = make()
        found = parse_detail((FIXTURES / "devpost_detail.html").read_text(encoding="utf-8"), h)
        self.assertTrue(found)
        self.assertEqual(h.deadline, datetime(2026, 12, 4, 17, 0, tzinfo=timezone(timedelta(hours=-5))))
        self.assertIn("Above legal age of majority in country of residence", h.eligibility)
        self.assertEqual(h.countries_mode, "excluded")
        self.assertIn("Italy", h.countries)
        self.assertNotIn("Nigeria", h.countries)

    def test_unknown_layout(self):
        self.assertFalse(parse_detail("<html><body>new design</body></html>", make()))


class LagosTimeTest(unittest.TestCase):
    def test_deadline_counted_in_lagos(self):
        # 23:30 US Eastern on Dec 4 is already Dec 5 in Lagos.
        h = make(deadline=datetime(2026, 12, 4, 23, 30, tzinfo=timezone(timedelta(hours=-5))))
        self.assertEqual(h.days_left(date(2026, 11, 15)), 20)

    def test_today_rolls_over_at_lagos_midnight(self):
        self.assertEqual(today_lagos(datetime(2026, 11, 15, 23, 30, tzinfo=timezone.utc)), date(2026, 11, 16))


if __name__ == "__main__":
    unittest.main()
