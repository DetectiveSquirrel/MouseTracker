from __future__ import annotations

import math
import time
from collections import deque
from typing import Any

# x, y, speed, born_at (perf_counter)
TrailPoint = tuple[float, float, float, float]


def _open_step(pos: float, vel: float, lo: float, hi: float, ease: float) -> float:
    """Move in an open interval (lo, hi). Remaining space is treated as infinite,
    so the cursor eases toward a wall and never lands on it. Away from the wall
    a step is nearly 1:1, like an FPS mouse with no bounds.
    """
    if vel == 0.0:
        return 0.0
    room = (hi - pos) if vel > 0.0 else (pos - lo)
    if room <= 0.0:
        return 0.0
    half = max((hi - lo) * 0.5, 1.0)
    # Center: k=1, step ≈ vel. Near a wall: extra ease, still never arrives.
    k = 1.0 + ease * (1.0 - min(room / half, 1.0))
    scale = max(room * k, 1.0)
    traveled = room * (1.0 - math.exp(-abs(vel) / scale))
    return traveled if vel > 0.0 else -traveled


class VirtualCursor:
    def __init__(self, width: int, height: int) -> None:
        self.width = float(max(width, 64))
        self.height = float(max(height, 64))
        self.x = self.width / 2.0
        self.y = self.height / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self._map = False
        self._next_trim: float | None = None
        self.trail: deque[TrailPoint] = deque(maxlen=128)

    def resize(self, width: int, height: int) -> None:
        width = float(max(int(width), 64))
        height = float(max(int(height), 64))
        if width == self.width and height == self.height:
            return
        sx = width / self.width
        sy = height / self.height
        self.width = width
        self.height = height
        if self._map:
            return
        self.x *= sx
        self.y *= sy
        self.trail = deque(
            ((x * sx, y * sy, speed, born) for x, y, speed, born in self.trail),
            maxlen=self.trail.maxlen,
        )

    def set_length(self, length: int) -> None:
        length = max(2, int(length))
        if self.trail.maxlen == length:
            return
        self.trail = deque(self.trail, maxlen=length)

    def clear(self) -> None:
        self.trail.clear()
        self._next_trim = None

    def expire(self, now: float | None = None, lifetime: float = 0.0) -> None:
        """Cut the oldest point after lifetime seconds, then restart the timer.

        0 keeps length-only behaviour. The live cursor point is kept.
        """
        lifetime = max(float(lifetime), 0.0)
        now = time.perf_counter() if now is None else now
        if lifetime <= 0.0 or len(self.trail) <= 1:
            self._next_trim = None
            return
        if self._next_trim is None:
            self._next_trim = now + lifetime
            return
        if now < self._next_trim:
            return
        self.trail.popleft()
        self._next_trim = None if len(self.trail) <= 1 else now + lifetime

    def reset_center(self) -> None:
        self.x = self.width / 2.0
        self.y = self.height / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.trail.clear()
        self._next_trim = None

    def step(self, dx: float, dy: float, cfg: dict[str, Any], screen_w: int, screen_h: int) -> None:
        self.set_length(int(cfg["line_length"]))
        weight = max(float(cfg["tracking_weight"]), 1.0)
        sensitivity = max(float(cfg["sensitivity"]), 0.05)
        inertia = min(max(float(cfg["inertia"]), 0.0), 0.95)
        ease = min(max(float(cfg.get("edge_spring", 0.0)), 0.0), 1.0)

        # A full swipe across the monitor fills this window when weight == 50.
        gain = sensitivity * (50.0 / weight)
        instant_x = dx * (self.width / max(screen_w, 1)) * gain
        instant_y = dy * (self.height / max(screen_h, 1)) * gain

        self.vx = self.vx * inertia + instant_x * (1.0 - inertia)
        self.vy = self.vy * inertia + instant_y * (1.0 - inertia)

        prev_x, prev_y = self.x, self.y
        self._map = str(cfg.get("view_mode", "window")).strip().lower() == "map"
        if self._map:
            self.x += self.vx
            self.y += self.vy
            if abs(self.x) > 8000.0 or abs(self.y) > 8000.0:
                shift_x, shift_y = self.x, self.y
                self.x = 0.0
                self.y = 0.0
                prev_x -= shift_x
                prev_y -= shift_y
                self.trail = deque(
                    ((x - shift_x, y - shift_y, speed, born) for x, y, speed, born in self.trail),
                    maxlen=self.trail.maxlen,
                )
        else:
            if ease <= 0.0:
                self.x += self.vx
                self.y += self.vy
                if self.x < 0.0:
                    self.x = 0.0
                    self.vx = 0.0
                elif self.x > self.width:
                    self.x = self.width
                    self.vx = 0.0
                if self.y < 0.0:
                    self.y = 0.0
                    self.vy = 0.0
                elif self.y > self.height:
                    self.y = self.height
                    self.vy = 0.0
            else:
                step_x = _open_step(self.x, self.vx, 0.0, self.width, ease)
                step_y = _open_step(self.y, self.vy, 0.0, self.height, ease)
                self.x += step_x
                self.y += step_y
                self.x = min(max(self.x, 0.0), self.width)
                self.y = min(max(self.y, 0.0), self.height)
                self.vx = step_x
                self.vy = step_y

        now = time.perf_counter()
        self.expire(now, float(cfg.get("trail_lifetime", 0.0)))

        speed = math.hypot(self.vx, self.vy)
        moved = speed > 0.02 or abs(instant_x) > 0.001 or abs(instant_y) > 0.001
        if not moved and self.trail:
            last_x, last_y, last_speed, born = self.trail[-1]
            self.trail[-1] = (self.x, self.y, last_speed, born)
            return

        if self.trail:
            last_x, last_y, _last_speed, _born = self.trail[-1]
            if math.hypot(self.x - last_x, self.y - last_y) < 0.7:
                self.trail[-1] = (self.x, self.y, speed, now)
                return
            gap = math.hypot(self.x - prev_x, self.y - prev_y)
            steps = max(int(gap / 3.0), 1)
            for i in range(1, steps):
                t = i / steps
                self.trail.append(
                    (prev_x + (self.x - prev_x) * t, prev_y + (self.y - prev_y) * t, speed, now)
                )
        self.trail.append((self.x, self.y, speed, now))
