import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hackhunt.scoring import interest_points, prize_points, registration_points, score, time_points
from hackhunt.storage import SeenStore

from .helpers import TODAY, make, settings


class ScoringTest(unittest.TestCase):
    def test_interest_match_uses_whole_words(self):
        interests = settings().interests
        pts, why = interest_points(make(themes=["Machine Learning/AI", "Fintech"]), interests)
        self.assertEqual(pts, 20)
        self.assertEqual(why, "matches AI/agents, Fintech")
        # "ai" must not match inside other words
        self.assertEqual(interest_points(make(title="Rails Mainframe Hack"), interests)[0], 0)

    def test_prize_log_scaled_usd(self):
        small, big = prize_points(make(prize_usd=1000)), prize_points(make(prize_usd=100000))
        self.assertAlmostEqual(small[0], 12, places=1)
        self.assertAlmostEqual(big[0], 20, places=1)
        self.assertEqual(big[1], "$100,000 prize")

    def test_non_usd_prize_is_neutral(self):
        pts, why = prize_points(make(prize_usd=None, prize_text="€5,000"))
        self.assertEqual(pts, 0)
        self.assertIn("€5,000", why)

    def test_time_sweet_spot(self):
        self.assertGreater(time_points(14)[0], time_points(6)[0])
        self.assertGreater(time_points(14)[0], time_points(45)[0])
        self.assertGreater(time_points(45)[0], time_points(90)[0])

    def test_fewer_registrations_bonus(self):
        self.assertGreater(registration_points(100)[0], registration_points(20000)[0])

    def test_breakdown_and_ranking(self):
        good = make(themes=["Machine Learning/AI"], prize_usd=20000, prize_text="$20,000", registrations=150)
        meh = make(themes=["Gaming"], prize_usd=500, prize_text="$500", registrations=9000,
                   end_date=date(2027, 3, 1))
        for h in (good, meh):
            score(h, settings().interests, TODAY)
        self.assertGreater(good.score, meh.score)
        self.assertEqual(set(good.score_breakdown), {"interests", "prize", "time", "registrations"})
        self.assertEqual(good.score, sum(p for p, _ in good.score_breakdown.values()))
        self.assertIn("matches AI/agents", good.score_reason)


class StorageTest(unittest.TestCase):
    def test_round_trip_keeps_exact_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "seen.json"
            now = datetime(2026, 11, 15, 6, tzinfo=timezone.utc)
            h = make(deadline=datetime(2026, 12, 4, 17, tzinfo=timezone(timedelta(hours=-5))))
            score(h, settings().interests, TODAY)
            store = SeenStore(path)
            store.mark_digested(h, now)
            store.save()

            entry = SeenStore(path).get(h.id)
            self.assertEqual(entry["status"], "digested")
            again = make()
            SeenStore.restore(again, entry)
            self.assertEqual(again.deadline, h.deadline)

    def test_prune_drops_long_finished(self):
        with tempfile.TemporaryDirectory() as d:
            store = SeenStore(Path(d) / "seen.json")
            now = datetime(2026, 11, 15, tzinfo=timezone.utc)
            store.mark_dropped(make(id="old", end_date=date(2026, 9, 1)), "x", now)
            store.mark_dropped(make(id="new"), "x", now)
            store.prune(TODAY)
            self.assertEqual(list(store.entries), ["new"])


if __name__ == "__main__":
    unittest.main()
