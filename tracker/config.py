from __future__ import annotations

import copy
import json
import threading
import time
from typing import Any

from tracker.paths import config_path

CHROMA_MAGENTA = [255, 0, 255]

DEFAULTS: dict[str, Any] = {
    "tracking_weight": 50.0,
    "inertia": 0.12,
    "edge_spring": 0.4,
    "view_mode": "window",
    "sensitivity": 1.0,
    "trail_style": "line",
    "thickness": 2.0,
    "line_length": 128,
    "trail_lifetime": 0.0,
    "fade": 0.35,
    "glow": 0.0,
    "opacity": 1.0,
    "taper": 0.75,
    "outline": 2.0,
    "outline_color": [0, 0, 0],
    "cursor_size": 7.0,
    "cursor_follow_color": True,
    "cursor_angle": 0,
    "head_marker": "crosshair",
    "color_mode": "solid",
    "line_color": [0, 0, 0],
    "head_color": [0, 0, 0],
    "tail_color": [120, 120, 120],
    "hue_min": 120.0,
    "hue_max": 0.0,
    "hue_span": 260.0,
    "bg_color": [255, 255, 255],
    "use_chroma": False,
    "particles_enabled": False,
    "particle_amount": 12,
    "particle_size": 2.5,
    "particle_lifetime": 0.45,
    "particle_follow_color": True,
    "particle_color": [255, 255, 255],
    "window_size": 512,
    "window_ratio": "monitor",
    "window_ratio_w": 16,
    "window_ratio_h": 9,
    "always_on_top": False,
    "borderless": False,
    "obs_mode": True,
    "capture_fps": 60,
    "show_clicks": False,
    "show_perf": False,
    "show_perf_overlay": False,
    "font_size": 16,
    "counter_color": [0, 0, 0],
    "active_profile": "Classic",
    "profiles": {},
}

PRESETS: dict[str, dict[str, Any]] = {
    "Classic": {
        "trail_style": "line",
        "thickness": 1.4,
        "line_length": 128,
        "fade": 0.15,
        "glow": 0.0,
        "opacity": 1.0,
        "taper": 0.0,
        "outline": 1.4,
        "cursor_size": 5.0,
        "head_marker": "crosshair",
        "color_mode": "solid",
        "line_color": [0, 0, 0],
        "head_color": [0, 0, 0],
        "tail_color": [80, 80, 80],
        "bg_color": [255, 255, 255],
        "use_chroma": False,
        "particles_enabled": False,
        "counter_color": [0, 0, 0],
        "tracking_weight": 50.0,
        "inertia": 0.05,
        "edge_spring": 0.35,
    },
    "Neon": {
        "trail_style": "ribbon",
        "thickness": 3.5,
        "line_length": 160,
        "fade": 0.7,
        "glow": 0.75,
        "opacity": 1.0,
        "taper": 0.85,
        "outline": 2.2,
        "cursor_size": 8.0,
        "cursor_follow_color": True,
        "head_marker": "crosshair",
        "color_mode": "velocity",
        "line_color": [0, 255, 210],
        "head_color": [255, 80, 200],
        "tail_color": [40, 0, 80],
        "hue_min": 160.0,
        "hue_max": 15.0,
        "hue_span": 260.0,
        "bg_color": [255, 0, 255],
        "use_chroma": True,
        "particles_enabled": True,
        "particle_amount": 18,
        "particle_size": 2.2,
        "particle_lifetime": 0.4,
        "particle_follow_color": True,
        "counter_color": [255, 255, 255],
        "tracking_weight": 40.0,
        "inertia": 0.18,
        "edge_spring": 0.45,
    },
    "Rainbow": {
        "trail_style": "ribbon",
        "thickness": 9.0,
        "line_length": 180,
        "fade": 0.55,
        "glow": 0.45,
        "opacity": 1.0,
        "taper": 0.9,
        "outline": 2.4,
        "cursor_size": 10.0,
        "cursor_follow_color": True,
        "head_marker": "crosshair",
        "color_mode": "rainbow",
        "line_color": [80, 255, 140],
        "head_color": [80, 255, 140],
        "tail_color": [80, 255, 140],
        "hue_min": 120.0,
        "hue_max": 0.0,
        "hue_span": 280.0,
        "bg_color": [255, 0, 255],
        "use_chroma": True,
        "particles_enabled": False,
        "counter_color": [255, 255, 255],
        "tracking_weight": 42.0,
        "inertia": 0.14,
        "edge_spring": 0.42,
    },
    "Phosphor": {
        "trail_style": "ribbon",
        "thickness": 2.8,
        "line_length": 220,
        "fade": 0.85,
        "glow": 0.55,
        "opacity": 1.0,
        "taper": 0.8,
        "outline": 0.0,
        "cursor_size": 6.0,
        "head_marker": "crosshair",
        "color_mode": "age",
        "line_color": [80, 255, 90],
        "head_color": [180, 255, 160],
        "tail_color": [10, 60, 20],
        "bg_color": [0, 0, 0],
        "use_chroma": False,
        "particles_enabled": False,
        "counter_color": [80, 255, 90],
        "tracking_weight": 45.0,
        "inertia": 0.22,
        "edge_spring": 0.5,
    },
    "Ink": {
        "trail_style": "dots",
        "thickness": 3.5,
        "line_length": 90,
        "fade": 0.4,
        "glow": 0.0,
        "opacity": 0.9,
        "taper": 0.7,
        "outline": 1.8,
        "cursor_size": 0.0,
        "head_marker": "crosshair",
        "color_mode": "age",
        "line_color": [20, 20, 24],
        "head_color": [20, 20, 24],
        "tail_color": [160, 160, 168],
        "bg_color": [248, 246, 240],
        "use_chroma": False,
        "particles_enabled": False,
        "counter_color": [40, 40, 40],
        "tracking_weight": 55.0,
        "inertia": 0.08,
        "edge_spring": 0.38,
    },
}

PROFILE_META_KEYS = {"active_profile", "profiles", "custom_preset"}
SAVE_KEYS = set(DEFAULTS.keys())
_SAVE_DELAY = 0.35
_MAX_PROFILE_NAME = 40

RATIO_CHOICES = ["monitor", "square", "16:9", "16:10", "21:9", "4:3", "custom"]
_FIXED_RATIOS = {
    "square": (1, 1),
    "16:9": (16, 9),
    "16:10": (16, 10),
    "21:9": (21, 9),
    "4:3": (4, 3),
}


def clamp_capture_fps(value: Any) -> int:
    try:
        fps = int(round(float(value)))
    except (TypeError, ValueError):
        fps = 60
    return max(1, min(fps, 240))


def window_aspect(cfg: dict[str, Any], monitor_w: int = 16, monitor_h: int = 9) -> float:
    mode = str(cfg.get("window_ratio", "monitor")).strip().lower()
    if mode in {"monitor", "display", "auto"}:
        return max(float(monitor_w), 1.0) / max(float(monitor_h), 1.0)
    if mode == "custom":
        rw = max(int(cfg.get("window_ratio_w", 16)), 1)
        rh = max(int(cfg.get("window_ratio_h", 9)), 1)
        return rw / rh
    if mode in _FIXED_RATIOS:
        rw, rh = _FIXED_RATIOS[mode]
        return rw / rh
    if ":" in mode:
        left, right = mode.split(":", 1)
        try:
            return max(float(left), 0.05) / max(float(right), 0.05)
        except ValueError:
            pass
    return 1.0


def window_dims(cfg: dict[str, Any], monitor_w: int, monitor_h: int) -> tuple[int, int]:
    height = max(int(cfg.get("window_size", 512)), 64)
    height = min(height, 1200)
    width = int(round(height * window_aspect(cfg, monitor_w, monitor_h)))
    return max(64, min(width, 1920)), height


def _coerce_value(default: Any, value: Any) -> Any:
    if default is None:
        return copy.deepcopy(value)
    if isinstance(default, list) and isinstance(value, (list, tuple)) and len(value) == len(default):
        inner = type(default[0]) if default else float
        return [inner(v) for v in value]
    if isinstance(default, bool):
        return bool(value)
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    if isinstance(default, str):
        return str(value)
    return copy.deepcopy(value)


def sanitize_profile_name(name: Any) -> str:
    text = " ".join(str(name or "").split())
    return text[:_MAX_PROFILE_NAME]


def is_builtin_profile(name: str) -> bool:
    return name in PRESETS


def profile_names(data: dict[str, Any]) -> list[str]:
    extras = [name for name in (data.get("profiles") or {}) if name and name not in PRESETS]
    extras.sort(key=str.casefold)
    return list(PRESETS.keys()) + extras


def snapshot_profile(data: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(data[key]) for key in SAVE_KEYS if key not in PROFILE_META_KEYS}


def _load_profiles(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not raw:
        return profiles
    incoming = raw.get("profiles")
    if isinstance(incoming, dict):
        for name, preset in incoming.items():
            clean = sanitize_profile_name(name)
            if not clean or clean in PRESETS or not isinstance(preset, dict):
                continue
            profiles[clean] = copy.deepcopy(preset)
    legacy = raw.get("custom_preset")
    if isinstance(legacy, dict):
        profiles.setdefault("Custom", copy.deepcopy(legacy))
    return profiles


def _merge_defaults(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = copy.deepcopy(DEFAULTS)
    if not raw:
        return data
    for key, default in DEFAULTS.items():
        if key in {"profiles", "custom_preset"} or key not in raw:
            continue
        try:
            data[key] = _coerce_value(default, raw[key])
        except (TypeError, ValueError):
            pass
    data["head_marker"] = "crosshair"
    data["profiles"] = _load_profiles(raw)
    active = sanitize_profile_name(raw.get("active_profile") or data["active_profile"])
    if active not in PRESETS and active not in data["profiles"]:
        active = "Classic"
    data["active_profile"] = active
    if "capture_fps" not in raw and isinstance(raw.get("poll_hz"), (int, float)):
        hz = int(raw["poll_hz"])
        data["capture_fps"] = 60 if hz > 120 else max(15, hz)
    return data


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        data = copy.deepcopy(DEFAULTS)
        save_config(data)
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("config is not an object")
        return _merge_defaults(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        return copy.deepcopy(DEFAULTS)


def save_config(data: dict[str, Any]) -> None:
    path = config_path()
    payload = {key: copy.deepcopy(data[key]) for key in SAVE_KEYS if key in data}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def apply_profile(data: dict[str, Any], name: str) -> dict[str, Any]:
    if name in PRESETS:
        merged = copy.deepcopy(data)
        merged.update(copy.deepcopy(PRESETS[name]))
        merged["head_marker"] = "crosshair"
        merged["active_profile"] = name
        return merged
    profiles = data.get("profiles") or {}
    preset = profiles.get(name)
    if not isinstance(preset, dict):
        return data
    merged = _merge_defaults({**data, **preset})
    merged["profiles"] = copy.deepcopy(profiles)
    merged["active_profile"] = name
    return merged


def put_profile(data: dict[str, Any], name: str) -> dict[str, Any]:
    name = sanitize_profile_name(name)
    if not name:
        raise ValueError("Profile name is empty.")
    if name in PRESETS:
        raise ValueError(f'"{name}" is a built-in look. Choose another name.')
    out = copy.deepcopy(data)
    profiles = dict(out.get("profiles") or {})
    profiles[name] = snapshot_profile(out)
    out["profiles"] = profiles
    out["active_profile"] = name
    return out


def rename_profile(data: dict[str, Any], old_name: str, new_name: str) -> dict[str, Any]:
    old_name = sanitize_profile_name(old_name)
    new_name = sanitize_profile_name(new_name)
    if old_name in PRESETS:
        raise ValueError("Built-in looks cannot be renamed.")
    if not new_name:
        raise ValueError("Profile name is empty.")
    if new_name in PRESETS:
        raise ValueError(f'"{new_name}" is a built-in look. Choose another name.')
    profiles = dict(data.get("profiles") or {})
    if old_name not in profiles:
        raise ValueError(f'No profile named "{old_name}".')
    if new_name != old_name and new_name in profiles:
        raise ValueError(f'A profile named "{new_name}" already exists.')
    out = copy.deepcopy(data)
    stored = profiles.pop(old_name)
    profiles[new_name] = stored
    out["profiles"] = profiles
    if out.get("active_profile") == old_name:
        out["active_profile"] = new_name
    return out


def delete_profile(data: dict[str, Any], name: str) -> dict[str, Any]:
    name = sanitize_profile_name(name)
    if name in PRESETS:
        raise ValueError("Built-in looks cannot be deleted.")
    out = copy.deepcopy(data)
    profiles = dict(out.get("profiles") or {})
    profiles.pop(name, None)
    out["profiles"] = profiles
    if out.get("active_profile") == name:
        out = apply_profile(out, "Classic")
    return out


_put_profile = put_profile
_rename_profile = rename_profile
_delete_profile = delete_profile


class ConfigStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = load_config()
        self._dirty = False
        self._last_change = 0.0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(key, default))

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            changed = False
            for key, value in kwargs.items():
                if key not in SAVE_KEYS:
                    continue
                if self._data.get(key) != value:
                    self._data[key] = copy.deepcopy(value)
                    changed = True
            if changed:
                self._dirty = True
                self._last_change = time.monotonic()

    def replace(self, data: dict[str, Any]) -> None:
        with self._lock:
            profiles = self._data.get("profiles")
            self._data = _merge_defaults(data)
            if isinstance(data.get("profiles"), dict):
                self._data["profiles"] = _load_profiles(data)
            elif profiles:
                self._data["profiles"] = copy.deepcopy(profiles)
            self._dirty = True
            self._last_change = time.monotonic()

    def save_profile(self, name: str) -> str:
        with self._lock:
            self._data = _put_profile(self._data, name)
            self._dirty = True
            self._last_change = time.monotonic()
            return str(self._data["active_profile"])

    def rename_profile(self, old_name: str, new_name: str) -> str:
        with self._lock:
            self._data = _rename_profile(self._data, old_name, new_name)
            self._dirty = True
            self._last_change = time.monotonic()
            return str(self._data.get("active_profile") or new_name)

    def delete_profile(self, name: str) -> str:
        with self._lock:
            self._data = _delete_profile(self._data, name)
            self._dirty = True
            self._last_change = time.monotonic()
            return str(self._data.get("active_profile") or "Classic")

    def save_now(self) -> None:
        with self._lock:
            save_config(self._data)
            self._dirty = False

    def maybe_save(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            if time.monotonic() - self._last_change < _SAVE_DELAY:
                return
            save_config(self._data)
            self._dirty = False
