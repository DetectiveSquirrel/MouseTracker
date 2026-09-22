from __future__ import annotations

import os
import time
import traceback

import pygame

from tracker import WINDOW_TITLE
from tracker.config import ConfigStore, clamp_capture_fps, window_dims
from tracker.mouse import MouseState
from tracker.paths import crash_log_path
from tracker.perf import PerfMonitor
from tracker.physics import VirtualCursor
from tracker.render import Renderer
from tracker.settings_ui import SettingsWindow
from tracker.win32 import (
    VK_MENU,
    configure_overlay,
    cursor_monitor_size,
    cursor_position,
    enable_dpi_awareness,
    key_down,
    move_window,
    set_always_on_top,
    show_error,
    window_position,
)


def _make_window(width: int, height: int, borderless: bool, click_through: bool) -> pygame.Surface:
    flags = pygame.NOFRAME if borderless else 0
    screen = pygame.display.set_mode((width, height), flags)
    pygame.display.set_caption(WINDOW_TITLE)
    pygame.event.set_grab(False)
    configure_overlay(click_through)
    return screen


def run_app() -> None:
    store = ConfigStore()
    running = True

    def request_quit() -> None:
        nonlocal running
        running = False

    # Tk must start before pygame when frozen, so Tcl/Tk finds its libraries.
    settings = SettingsWindow(store)
    settings.set_on_close(request_quit)

    pygame.init()
    pygame.font.init()
    pygame.event.set_grab(False)

    cfg = store.snapshot()
    monitor_w, monitor_h = cursor_monitor_size()
    width, height = window_dims(cfg, monitor_w, monitor_h)
    borderless = True if cfg["obs_mode"] else bool(cfg["borderless"])
    always_on_top = bool(cfg["always_on_top"])
    click_through = bool(cfg["obs_mode"])

    screen = _make_window(width, height, borderless, click_through)
    set_always_on_top(always_on_top)
    configure_overlay(click_through)

    physics = VirtualCursor(width, height)
    renderer = Renderer(width, height)
    mouse_state = MouseState()
    mouse_state.set_poll_hz(clamp_capture_fps(cfg["capture_fps"]))
    mouse_state.start()
    perf = PerfMonitor()
    clock = pygame.time.Clock()
    dragging = False
    drag_cursor = (0, 0)
    drag_window = (0, 0)
    last_perf_ui = 0.0
    last_capture = 0.0

    try:
        while running:
            dt = min(clock.tick(60) / 1000.0, 0.05)
            settings.pump()
            if not running:
                break
            store.maybe_save()
            cfg = store.snapshot()
            capture_fps = clamp_capture_fps(cfg["capture_fps"])
            mouse_state.set_poll_hz(capture_fps)

            monitor_w, monitor_h = cursor_monitor_size()
            new_w, new_h = window_dims(cfg, monitor_w, monitor_h)
            new_borderless = True if cfg["obs_mode"] else bool(cfg["borderless"])
            alt_move = key_down(VK_MENU)
            new_click_through = bool(cfg["obs_mode"]) and not alt_move and not dragging
            if new_w != width or new_h != height or new_borderless != borderless:
                width, height = new_w, new_h
                borderless = new_borderless
                click_through = new_click_through
                screen = _make_window(width, height, borderless, click_through)
                physics.resize(width, height)
                renderer.resize(width, height)
                set_always_on_top(bool(cfg["always_on_top"]))
                always_on_top = bool(cfg["always_on_top"])
                configure_overlay(click_through)
            else:
                if new_click_through != click_through:
                    click_through = new_click_through
                    configure_overlay(click_through)
                if bool(cfg["always_on_top"]) != always_on_top:
                    always_on_top = bool(cfg["always_on_top"])
                    set_always_on_top(always_on_top)
                    configure_overlay(click_through)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        physics.clear()
                    elif event.key == pygame.K_h:
                        settings.toggle()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and borderless:
                    dragging = True
                    drag_cursor = cursor_position()
                    drag_window = window_position()
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False

            if dragging:
                if not borderless or not pygame.mouse.get_pressed()[0]:
                    dragging = False
                else:
                    cx, cy = cursor_position()
                    move_window(
                        drag_window[0] + (cx - drag_cursor[0]),
                        drag_window[1] + (cy - drag_cursor[1]),
                    )

            now = time.perf_counter()
            if now - last_capture >= 1.0 / capture_fps:
                last_capture = now
                perf.begin_update()
                samples = mouse_state.consume_samples()
                dx = sum(sample[0] for sample in samples)
                dy = sum(sample[1] for sample in samples)
                physics.step(dx, dy, cfg, monitor_w, monitor_h)
                perf.end_update(capture_fps, len(physics.trail))
                perf_text = perf.text() if cfg["show_perf"] or cfg["show_perf_overlay"] else ""
                if cfg["show_perf"]:
                    ui_now = pygame.time.get_ticks() / 1000.0
                    if ui_now - last_perf_ui > 0.25:
                        settings.set_perf_text(perf_text)
                        last_perf_ui = ui_now
                renderer.draw(
                    screen,
                    list(physics.trail),
                    cfg,
                    mouse_state.click_count(),
                    1.0 / capture_fps,
                    perf_text=perf_text if cfg["show_perf_overlay"] else None,
                )
                pygame.display.flip()
    finally:
        store.save_now()
        mouse_state.stop()
        settings.destroy()
        pygame.quit()


def main() -> None:
    os.environ.setdefault("SDL_HINT_FORCE_RAISEWINDOW", "0")
    os.environ.setdefault("SDL_MOUSE_FOCUS_CLICKTHROUGH", "1")
    enable_dpi_awareness()
    try:
        run_app()
    except Exception:
        details = traceback.format_exc()
        try:
            crash_log_path().write_text(details, encoding="utf-8")
        except OSError:
            pass
        show_error(
            "Mouse Tracker",
            "Something went wrong. A crash.log was saved next to the app.\n\n" + details[-1500:],
        )
        raise


if __name__ == "__main__":
    main()
