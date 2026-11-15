import unittest
from datetime import date

from hackhunt.filters import basic_drop_reason, eligibility_drop_reason, reminder_due

from .helpers import TODAY, make, settings


class BasicTest(unittest.TestCase):
    def test_keeps_good_one(self):
        self.assertIsNone(basic_drop_reason(make(), settings(), TODAY))

    def test_in_person(self):
        self.assertIn("not online", basic_drop_reason(make(online=False, location="Lagos"), settings(), TODAY))
        self.assertIsNone(basic_drop_reason(make(online=False), settings(online_only=False), TODAY))

    def test_invite_only(self):
        self.assertEqual(basic_drop_reason(make(invite_only=True), settings(), TODAY), "invite only")

    def test_min_days_left(self):
        self.assertIsNone(basic_drop_reason(make(end_date=date(2026, 11, 20)), settings(), TODAY))
        self.assertIn("4 days left", basic_drop_reason(make(end_date=date(2026, 11, 19)), settings(), TODAY))

    def test_no_deadline(self):
        self.assertEqual(basic_drop_reason(make(end_date=None), settings(), TODAY), "no deadline found")


class EligibilityTest(unittest.TestCase):
    def test_nigeria_excluded(self):
        h = make(countries_mode="excluded", countries=["Cuba", "Nigeria"])
        self.assertIn("excluded", eligibility_drop_reason(h, settings()))

    def test_other_countries_excluded(self):
        self.assertIsNone(eligibility_drop_reason(make(countries_mode="excluded", countries=["Cuba"]), settings()))

    def test_allowed_list_without_nigeria(self):
        h = make(countries_mode="included", countries=["Canada", "United States"])
        self.assertIn("allowed", eligibility_drop_reason(h, settings()))
        h.countries.append("Nigeria")
        self.assertIsNone(eligibility_drop_reason(h, settings()))

    def test_phrase(self):
        h = make(eligibility=["Ages 18+ only", "Not open to students of partner schools"])
        self.assertEqual(eligibility_drop_reason(h, settings()), 'eligibility says "not open to students"')

    def test_unclear_text_is_kept(self):
        self.assertIsNone(eligibility_drop_reason(make(eligibility=["Ages 18+ only"]), settings()))


class ReminderTest(unittest.TestCase):
    def test_due_once_inside_window(self):
        h = make(end_date=date(2026, 11, 18))
        self.assertTrue(reminder_due(h, {"status": "digested"}, TODAY, 3))
        self.assertFalse(reminder_due(h, {"status": "digested", "urgent_flagged_at": "x"}, TODAY, 3))
        self.assertFalse(reminder_due(h, {"status": "dropped"}, TODAY, 3))

    def test_not_due_outside_window(self):
        self.assertFalse(reminder_due(make(end_date=date(2026, 11, 19)), {"status": "digested"}, TODAY, 3))
        self.assertFalse(reminder_due(make(end_date=date(2026, 11, 14)), {"status": "digested"}, TODAY, 3))


if __name__ == "__main__":
    unittest.main()
