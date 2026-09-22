from __future__ import annotations

import threading
import time

from tracker.win32 import (
    VK_LBUTTON,
    VK_MBUTTON,
    VK_RBUTTON,
    RawInputListener,
    cursor_position,
    key_down,
    set_timer_resolution,
)


class MouseState:
    """Relative mouse motion the way games read it (raw input), listen-only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._last: tuple[float, float] | None = None
        self.clicks = 0
        self._poll_hz = 60
        self._running = False
        self._poll_thread: threading.Thread | None = None
        self._prev_buttons = (False, False, False)
        self._raw = RawInputListener()
        self._use_raw = False

    def set_poll_hz(self, hz: int) -> None:
        with self._lock:
            self._poll_hz = max(1, min(int(hz), 240))

    def consume_samples(self) -> list[tuple[float, float]]:
        with self._lock:
            dx, dy = self._acc_x, self._acc_y
            self._acc_x = 0.0
            self._acc_y = 0.0
        if dx or dy:
            return [(dx, dy)]
        return []

    def click_count(self) -> int:
        with self._lock:
            return self.clicks

    def _add(self, dx: float, dy: float) -> None:
        if not dx and not dy:
            return
        with self._lock:
            self._acc_x += float(dx)
            self._acc_y += float(dy)

    def _note_clicks(self) -> None:
        buttons = (key_down(VK_LBUTTON), key_down(VK_RBUTTON), key_down(VK_MBUTTON))
        pressed = sum(1 for now, was in zip(buttons, self._prev_buttons) if now and not was)
        self._prev_buttons = buttons
        if pressed:
            with self._lock:
                self.clicks += pressed

    def _poll_loop(self) -> None:
        self._use_raw = self._raw.start(self._add)
        next_t = time.perf_counter()
        while self._running:
            if self._use_raw:
                self._raw.pump()
            else:
                x, y = cursor_position()
                with self._lock:
                    if self._last is not None:
                        self._acc_x += float(x - self._last[0])
                        self._acc_y += float(y - self._last[1])
                    self._last = (x, y)
            self._note_clicks()
            with self._lock:
                hz = self._poll_hz
            period = 1.0 / max(hz, 60)
            next_t += period
            now = time.perf_counter()
            delay = next_t - now
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.perf_counter()
        self._raw.stop()

    def start(self) -> None:
        set_timer_resolution(1)
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, name="mouse-poll", daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=0.5)
            self._poll_thread = None
        set_timer_resolution(0)
