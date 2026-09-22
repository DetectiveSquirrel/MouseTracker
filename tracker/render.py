from __future__ import annotations

import colorsys
import math
import random
from typing import Any

import pygame

from tracker.config import CHROMA_MAGENTA

_SS = 2
# OBS Color Key is #FF00FF (hue ~300°). Keep generated hues clear of that band
# so Similarity does not eat the trail.
_CHROMA_HUE = 300.0
_CHROMA_HUE_PAD = 42.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _hue_avoid_magenta(hue: float) -> float:
    h = hue % 360.0
    lo = _CHROMA_HUE - _CHROMA_HUE_PAD
    hi = _CHROMA_HUE + _CHROMA_HUE_PAD
    if lo < h < hi:
        return lo if h < _CHROMA_HUE else hi
    return h


def _rgb_avoid_magenta(r: int, g: int, b: int) -> tuple[int, int, int]:
    if r > 155 and b > 155 and g < 115:
        g = 115
        r = min(r, 195)
        b = min(b, 195)
    return r, g, b


def _mix_color(a: list[int] | tuple[int, ...], b: list[int] | tuple[int, ...], t: float) -> tuple[int, int, int]:
    t = _clamp(t, 0.0, 1.0)
    return _rgb_avoid_magenta(
        int(_lerp(a[0], b[0], t)),
        int(_lerp(a[1], b[1], t)),
        int(_lerp(a[2], b[2], t)),
    )


def _hsv_rgb(hue: float, sat: float = 1.0, val: float = 1.0) -> tuple[int, int, int]:
    hue = _hue_avoid_magenta(hue) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return _rgb_avoid_magenta(int(r * 255), int(g * 255), int(b * 255))


def _speed_t(speed: float) -> float:
    return _clamp(speed / 14.0, 0.0, 1.0)


def _smooth_speeds(speeds: list[float]) -> list[float]:
    if len(speeds) < 3:
        return speeds
    out = list(speeds)
    for i in range(1, len(speeds) - 1):
        out[i] = 0.2 * speeds[i - 1] + 0.6 * speeds[i] + 0.2 * speeds[i + 1]
    return out


def color_for_point(index: int, count: int, speed: float, cfg: dict[str, Any]) -> tuple[int, int, int, int]:
    if count <= 1:
        age_t = 1.0
    else:
        age_t = index / (count - 1)
    fade = _clamp(float(cfg["fade"]), 0.0, 1.0)
    alpha = int(255 * float(cfg["opacity"]) * (1.0 - (1.0 - age_t) * fade))
    alpha = max(alpha, 0)
    speed_t = _speed_t(speed)

    mode = cfg["color_mode"]
    if mode == "velocity":
        hue = _lerp(float(cfg["hue_min"]), float(cfg["hue_max"]), speed_t)
        rgb = _hsv_rgb(hue, 0.85 + 0.15 * speed_t, 0.7 + 0.3 * speed_t)
    elif mode == "rainbow":
        # Green (or hue_min) at both ends; middle of the trail runs through the spectrum.
        wave = math.sin(age_t * math.pi)
        hue = float(cfg["hue_min"]) + wave * float(cfg.get("hue_span", 260.0))
        rgb = _hsv_rgb(hue, 0.9, 0.72 + 0.28 * speed_t)
    elif mode == "age":
        rgb = _mix_color(cfg["tail_color"], cfg["head_color"], age_t)
    else:
        rgb = (int(cfg["line_color"][0]), int(cfg["line_color"][1]), int(cfg["line_color"][2]))
    return rgb[0], rgb[1], rgb[2], alpha


def _catmull_rom(points: list[tuple[float, float]], colors: list[tuple[int, int, int, int]], per_seg: int = 8):
    if len(points) < 2:
        return points, colors
    if len(points) == 2:
        return _densify(points, colors, 0.6)

    padded = [points[0], *points, points[-1]]
    color_pad = [colors[0], *colors, colors[-1]]
    out_p: list[tuple[float, float]] = []
    out_c: list[tuple[int, int, int, int]] = []

    def point_at(p0, p1, p2, p3, t: float) -> tuple[float, float]:
        t2 = t * t
        t3 = t2 * t
        x = 0.5 * (
            (2 * p1[0])
            + (-p0[0] + p2[0]) * t
            + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
            + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
        )
        y = 0.5 * (
            (2 * p1[1])
            + (-p0[1] + p2[1]) * t
            + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
            + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
        )
        return x, y

    def color_at(c0, c1, c2, c3, t: float) -> tuple[int, int, int, int]:
        return tuple(int(_clamp(_lerp(c1[i], c2[i], t), 0, 255)) for i in range(4))  # type: ignore[return-value]

    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        c0, c1, c2, c3 = color_pad[i - 1], color_pad[i], color_pad[i + 1], color_pad[i + 2]
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        samples = max(int(dist * per_seg / 6.0), per_seg)
        for s in range(samples):
            t = s / samples
            out_p.append(point_at(p0, p1, p2, p3, t))
            out_c.append(color_at(c0, c1, c2, c3, t))
    out_p.append(points[-1])
    out_c.append(colors[-1])
    return out_p, out_c


def _densify(
    points: list[tuple[float, float]],
    colors: list[tuple[int, int, int, int]],
    spacing: float,
) -> tuple[list[tuple[float, float]], list[tuple[int, int, int, int]]]:
    if len(points) < 2:
        return points, colors
    out_p = [points[0]]
    out_c = [colors[0]]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(int(dist / max(spacing, 0.25)), 1)
        c0, c1 = colors[i], colors[i + 1]
        for k in range(1, steps + 1):
            t = k / steps
            out_p.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            out_c.append(tuple(int(c0[j] + (c1[j] - c0[j]) * t) for j in range(4)))  # type: ignore[arg-type]
    return out_p, out_c


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        size: float,
        color: tuple[int, int, int],
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color


class Renderer:
    def __init__(self, width: int, height: int) -> None:
        self.width = max(int(width), 64)
        self.height = max(int(height), 64)
        self.hi = pygame.Surface((self.width * _SS, self.height * _SS), pygame.SRCALPHA)
        self.particles: list[Particle] = []
        self._font_cache: dict[int, pygame.font.Font] = {}
        self._zoom = 1.0

    def resize(self, width: int, height: int) -> None:
        width = max(int(width), 64)
        height = max(int(height), 64)
        if width == self.width and height == self.height:
            return
        sx = width / self.width
        sy = height / self.height
        self.width = width
        self.height = height
        self.hi = pygame.Surface((width * _SS, height * _SS), pygame.SRCALPHA)
        for particle in self.particles:
            particle.x *= sx
            particle.y *= sy

    def _font(self, size: int) -> pygame.font.Font:
        size = max(8, int(size))
        font = self._font_cache.get(size)
        if font is None:
            font = pygame.font.SysFont("segoeui", size) or pygame.font.Font(None, size)
            self._font_cache[size] = font
        return font

    def _spawn_particles(
        self,
        cfg: dict[str, Any],
        x: float,
        y: float,
        speed: float,
        rgb: tuple[int, int, int],
        dt: float,
    ) -> None:
        if not cfg["particles_enabled"] or speed < 0.4:
            return
        amount = float(cfg["particle_amount"])
        spawn = amount * _speed_t(speed) * dt * 8.0
        n = int(spawn)
        if random.random() < spawn - n:
            n += 1
        life = max(float(cfg["particle_lifetime"]), 0.05)
        size = max(float(cfg["particle_size"]), 0.5)
        color = tuple(int(c) for c in cfg["particle_color"]) if not cfg["particle_follow_color"] else rgb
        for _ in range(min(n, 24)):
            angle = random.uniform(0.0, math.tau)
            mag = random.uniform(8.0, 40.0) * (0.3 + _speed_t(speed))
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * mag,
                    math.sin(angle) * mag,
                    life * random.uniform(0.6, 1.1),
                    size * random.uniform(0.6, 1.3),
                    color,
                )
            )
        if len(self.particles) > 400:
            self.particles = self.particles[-400:]

    def _update_particles(self, dt: float) -> None:
        alive: list[Particle] = []
        for particle in self.particles:
            particle.life -= dt
            if particle.life <= 0:
                continue
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vx *= 0.92
            particle.vy *= 0.92
            alive.append(particle)
        self.particles = alive

    def _stamp_circle(self, x: float, y: float, radius: float, color: tuple[int, int, int, int]) -> None:
        pos = (x * _SS, y * _SS)
        rad = max(radius * _SS, 0.6)
        pygame.draw.circle(self.hi, color, pos, rad)
        try:
            pygame.draw.aacircle(self.hi, color, pos, rad)
        except (AttributeError, TypeError, ValueError):
            pass

    def _stamp_stroke(
        self,
        points: list[tuple[float, float]],
        colors: list[tuple[int, int, int, int]],
        thickness: float,
        glow: float,
        taper: float = 0.0,
    ) -> None:
        if not points:
            return
        smooth_p, smooth_c = _catmull_rom(points, colors)
        dense_p, dense_c = _densify(smooth_p, smooth_c, spacing=0.55)
        n = max(len(dense_p) - 1, 1)
        taper = _clamp(taper, 0.0, 1.0)
        head_r = max(thickness * 0.5, 0.45)
        tail_r = max(head_r * (1.0 - taper), 0.35)
        for i, ((x, y), color) in enumerate(zip(dense_p, dense_c)):
            t = i / n
            u = t * t * (3.0 - 2.0 * t)
            rad = _lerp(tail_r, head_r, u)
            if glow > 0:
                r, g, b, a = color
                self._stamp_circle(x, y, rad + glow * 6.0 * (0.35 + 0.65 * u), (r, g, b, max(a // 6, 1)))
            self._stamp_circle(x, y, rad, color)

    def _draw_ribbon(
        self,
        points: list[tuple[float, float]],
        colors: list[tuple[int, int, int, int]],
        thickness: float,
        glow: float,
        taper: float = 0.0,
    ) -> None:
        layers = (
            (thickness * 2.15, 0.2),
            (thickness * 1.35, 0.42),
            (thickness * 1.0, 1.0),
        )
        if glow > 0:
            glow_colors = [(r, g, b, max(a // 5, 1)) for r, g, b, a in colors]
            self._stamp_stroke(points, glow_colors, thickness + glow * 8.0, 0.0, taper)
        for width, alpha_mul in layers:
            layer_colors = [(r, g, b, max(int(a * alpha_mul), 1)) for r, g, b, a in colors]
            self._stamp_stroke(points, layer_colors, width, 0.0, taper)

    def _draw_dots(
        self,
        points: list[tuple[float, float]],
        colors: list[tuple[int, int, int, int]],
        thickness: float,
        taper: float = 0.0,
    ) -> None:
        n = max(len(points) - 1, 1)
        taper = _clamp(taper, 0.0, 1.0)
        head_r = max(thickness, 0.8)
        tail_r = max(head_r * (1.0 - taper), 0.5)
        step = 1 if len(points) < 80 else 2
        for i in range(0, len(points), step):
            t = i / n
            u = t * t * (3.0 - 2.0 * t)
            self._stamp_circle(points[i][0], points[i][1], _lerp(tail_r, head_r, u), colors[i])

    def _draw_trail(
        self,
        points: list[tuple[float, float]],
        colors: list[tuple[int, int, int, int]],
        cfg: dict[str, Any],
        thickness: float,
        glow: float,
        taper: float,
    ) -> None:
        outline = max(float(cfg.get("outline", 0.0)), 0.0)
        style = cfg["trail_style"]
        if outline > 0.04:
            oc = [int(c) for c in cfg.get("outline_color", [0, 0, 0])]
            fringe = [(oc[0], oc[1], oc[2], a) for _r, _g, _b, a in colors]
            extra = outline * 2.0
            if style == "dots":
                self._draw_dots(points, fringe, thickness + extra, taper)
            else:
                self._stamp_stroke(points, fringe, thickness + extra, 0.0, taper)
        if style == "ribbon":
            self._draw_ribbon(points, colors, thickness, glow, taper)
        elif style == "dots":
            self._draw_dots(points, colors, thickness, taper)
        else:
            self._stamp_stroke(points, colors, thickness, glow, taper)

    def _line_arm(
        self,
        x: float,
        y: float,
        deg: float,
        span: float,
        color: tuple[int, int, int, int],
        width: float,
    ) -> None:
        rad = math.radians(deg)
        dx = math.cos(rad) * span
        dy = math.sin(rad) * span
        self._stamp_stroke([(x - dx, y - dy), (x + dx, y + dy)], [color, color], width, 0.0, 0.0)

    def _draw_head(
        self,
        cfg: dict[str, Any],
        pos: tuple[float, float],
        color: tuple[int, int, int, int],
    ) -> None:
        size = float(cfg.get("cursor_size", 6.0))
        if size <= 0.05:
            return
        if cfg.get("cursor_follow_color", True):
            fill = (*color[:3], 255)
        else:
            hc = cfg["head_color"]
            fill = (int(hc[0]), int(hc[1]), int(hc[2]), 255)
        oc = [int(c) for c in cfg.get("outline_color", [0, 0, 0])]
        edge = (oc[0], oc[1], oc[2], 255)
        outline = max(float(cfg.get("outline", 0.0)), 0.0)
        x, y = pos
        ang = float(cfg.get("cursor_angle", 0.0))
        width = max(size * 0.18, 1.1)
        span = max(size * 1.35, 5.0)

        def cross(col: tuple[int, int, int, int], extra: float = 0.0) -> None:
            self._line_arm(x, y, ang, span + extra, col, width + extra * 0.45)
            self._line_arm(x, y, ang + 90, span + extra, col, width + extra * 0.45)

        if outline > 0.04:
            cross(edge, outline * 0.55)
        cross(fill)
        self._stamp_circle(x, y, size * 0.26, fill)

    def _draw_particles(self, origin: tuple[float, float] | None = None) -> None:
        cx = self.width * 0.5
        cy = self.height * 0.5
        z = self._zoom if origin is not None else 1.0
        ox, oy = origin if origin is not None else (0.0, 0.0)
        for particle in self.particles:
            t = particle.life / particle.max_life
            alpha = max(int(220 * t), 0)
            radius = max(particle.size * (0.4 + 0.6 * t), 0.6)
            if origin is not None:
                x = cx + (particle.x - ox) * z
                y = cy + (particle.y - oy) * z
                radius = max(radius * max(z, 0.55), 0.5)
            else:
                x, y = particle.x, particle.y
            self._stamp_circle(x, y, radius, (*particle.color, alpha))

    def _rest_head_color(self, cfg: dict[str, Any]) -> tuple[int, int, int, int]:
        if cfg.get("cursor_follow_color", True):
            rgb = (int(cfg["line_color"][0]), int(cfg["line_color"][1]), int(cfg["line_color"][2]))
        else:
            hc = cfg["head_color"]
            rgb = (int(hc[0]), int(hc[1]), int(hc[2]))
        return rgb[0], rgb[1], rgb[2], 255

    def _map_view(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if not points:
            return points
        ox, oy = points[-1]
        self._zoom = 1.0
        cx = self.width * 0.5
        cy = self.height * 0.5
        return [(cx + (x - ox), cy + (y - oy)) for x, y in points]

    def draw(
        self,
        screen: pygame.Surface,
        trail: list[tuple[float, ...]],
        cfg: dict[str, Any],
        click_count: int,
        dt: float,
        perf_text: str | None = None,
    ) -> None:
        if cfg["obs_mode"] or cfg["use_chroma"]:
            bg = tuple(CHROMA_MAGENTA)
        else:
            bg = (int(cfg["bg_color"][0]), int(cfg["bg_color"][1]), int(cfg["bg_color"][2]))
        screen.fill(bg)
        self.hi.fill((0, 0, 0, 0))

        if trail:
            world_pts = [(point[0], point[1]) for point in trail]
            speeds = _smooth_speeds([point[2] for point in trail])
            colors = [
                color_for_point(i, len(trail), speed, cfg)
                for i, speed in enumerate(speeds)
            ]
            follow = str(cfg.get("view_mode", "window")).strip().lower() == "map"
            if follow:
                points = self._map_view(world_pts)
            else:
                self._zoom = 1.0
                points = world_pts
            thickness = max(float(cfg["thickness"]), 0.5)
            glow = _clamp(float(cfg["glow"]), 0.0, 1.0)
            taper = _clamp(float(cfg.get("taper", 0.0)), 0.0, 1.0)
            self._draw_trail(points, colors, cfg, thickness, glow, taper)

            head_rgb = colors[-1][:3]
            self._spawn_particles(cfg, trail[-1][0], trail[-1][1], trail[-1][2], head_rgb, dt)
            self._update_particles(dt)
            self._draw_particles(origin=world_pts[-1] if follow else None)
            self._draw_head(cfg, points[-1], colors[-1])
        else:
            self._update_particles(dt)
            self._draw_particles()
            rest = (self.width * 0.5, self.height * 0.5)
            self._draw_head(cfg, rest, self._rest_head_color(cfg))

        screen.blit(pygame.transform.smoothscale(self.hi, (self.width, self.height)), (0, 0))

        if cfg["show_clicks"]:
            font = self._font(int(cfg["font_size"]))
            text = font.render(str(click_count), True, tuple(int(c) for c in cfg["counter_color"]))
            screen.blit(text, (10, 8))

        if perf_text:
            font = self._font(14)
            y = 8
            for line in perf_text.splitlines():
                shadow = font.render(line, True, (0, 0, 0))
                label = font.render(line, True, (255, 255, 80))
                screen.blit(shadow, (11, y + 1))
                screen.blit(label, (10, y))
                y += 18
