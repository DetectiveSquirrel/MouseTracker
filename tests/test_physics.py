from __future__ import annotations

import unittest

from tracker.physics import VirtualCursor


def _trail(cursor: VirtualCursor, *xs: float) -> None:
    cursor.trail.clear()
    cursor._next_trim = None
    for x in xs:
        cursor.trail.append((x, 0.0, 1.0, 0.0))


class TrailLifetimeTests(unittest.TestCase):
    def test_zero_lifetime_never_trims(self) -> None:
        cursor = VirtualCursor(200, 200)
        _trail(cursor, 10.0, 20.0, 30.0)
        cursor.expire(100.0, 0.0)
        cursor.expire(110.0, 0.0)
        self.assertEqual([p[0] for p in cursor.trail], [10.0, 20.0, 30.0])

    def test_waits_full_lifetime_before_first_cut(self) -> None:
        cursor = VirtualCursor(200, 200)
        _trail(cursor, 10.0, 20.0, 30.0)
        cursor.expire(100.0, 1.0)
        cursor.expire(100.99, 1.0)
        self.assertEqual([p[0] for p in cursor.trail], [10.0, 20.0, 30.0])

    def test_one_point_per_interval_then_timer_resets(self) -> None:
        cursor = VirtualCursor(200, 200)
        _trail(cursor, 10.0, 20.0, 30.0)
        cursor.expire(100.0, 1.0)
        cursor.expire(101.0, 1.0)
        self.assertEqual([p[0] for p in cursor.trail], [20.0, 30.0])
        cursor.expire(101.5, 1.0)
        self.assertEqual([p[0] for p in cursor.trail], [20.0, 30.0])
        cursor.expire(102.0, 1.0)
        self.assertEqual([p[0] for p in cursor.trail], [30.0])

    def test_lifetime_never_removes_the_live_point(self) -> None:
        cursor = VirtualCursor(200, 200)
        _trail(cursor, 10.0)
        cursor.expire(100.0, 0.2)
        cursor.expire(108.0, 0.2)
        self.assertEqual(len(cursor.trail), 1)
        self.assertEqual(cursor.trail[0][0], 10.0)


if __name__ == "__main__":
    unittest.main()
