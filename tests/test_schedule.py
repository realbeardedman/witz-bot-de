import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schedule_plan as sp  # noqa: E402

UTC = dt.timezone.utc
CFG = {"slots": {"morning": 7, "evening": 19}, "posting_mode": "test"}


class ScheduleTests(unittest.TestCase):
    def test_winter_and_summer_crons(self):
        winter = dt.datetime(2026, 12, 10, 6, 20, tzinfo=UTC)
        summer = dt.datetime(2027, 7, 10, 5, 20, tzinfo=UTC)
        self.assertEqual(sp.scheduled_slot("17 6 * * *", winter, CFG["slots"]), "morning")
        self.assertIsNone(sp.scheduled_slot("17 5 * * *", winter, CFG["slots"]))
        self.assertEqual(sp.scheduled_slot("17 5 * * *", summer, CFG["slots"]), "morning")
        self.assertEqual(sp.scheduled_slot("17 18 * * *", winter, CFG["slots"]), "evening")
        self.assertEqual(sp.scheduled_slot("17 17 * * *", summer, CFG["slots"]), "evening")

    def test_test_mode_alternates_and_each_weekday_gets_both_slots(self):
        start = dt.date(2026, 11, 30)
        seen = {}
        for i in range(14):
            day = start + dt.timedelta(days=i)
            seen.setdefault(day.weekday(), set()).add(sp.wanted_slot(day, "test"))
        self.assertTrue(all(v == {"morning", "evening"} for v in seen.values()))
        self.assertEqual(sp.wanted_slot(start, "morning"), "morning")

    def test_only_one_post_per_berlin_day(self):
        now = dt.datetime(2026, 12, 10, 18, 20, tzinfo=UTC)
        day = now.date()
        cfg = dict(CFG, posting_mode="evening")
        ok, _ = sp.decide("17 18 * * *", now, cfg, [])
        self.assertTrue(ok)
        state = [{"posted": "2026-12-10T06:20+00:00"}]
        ok, reason = sp.decide("17 18 * * *", now, cfg, state)
        self.assertFalse(ok, reason)
        self.assertTrue(sp.posted_on(state, day))

    def test_manual_run_always_allowed(self):
        self.assertTrue(sp.decide("", dt.datetime.now(UTC), CFG, [{"posted": dt.datetime.now(UTC).isoformat()}])[0])


if __name__ == "__main__":
    unittest.main()
