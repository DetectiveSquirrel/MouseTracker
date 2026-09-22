from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox, simpledialog, ttk
from typing import Callable

from tracker import SETTINGS_TITLE, __version__
from tracker.config import (
    RATIO_CHOICES,
    ConfigStore,
    apply_profile,
    is_builtin_profile,
    profile_names,
    sanitize_profile_name,
)

STYLES = ["line", "ribbon", "dots"]
MODES = ["solid", "rainbow", "velocity", "age"]
VIEW_MODES = ["window", "map"]


class SettingsWindow:
    def __init__(self, store: ConfigStore) -> None:
        self.store = store
        self._loading = False
        self._vars: dict[str, tk.Variable] = {}
        self._value_labels: dict[str, tuple[ttk.Label, str]] = {}
        self._color_previews: dict[str, tk.Label] = {}
        self._on_close: Callable[[], None] | None = None

        self.root = tk.Tk()
        self.root.title(SETTINGS_TITLE)
        self.root.geometry("392x620")
        self.root.minsize(360, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        style = ttk.Style(self.root)
        style.configure("TNotebook.Tab", padding=(10, 4))
        style.configure("TLabelframe", padding=6)
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))

        outer = ttk.Frame(self.root, padding=(8, 6, 8, 6))
        outer.pack(fill="both", expand=True)

        self._build_preset_bar(outer)

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True, pady=(4, 4))

        look = ttk.Frame(notebook, padding=8)
        color = ttk.Frame(notebook, padding=8)
        motion = ttk.Frame(notebook, padding=8)
        window = ttk.Frame(notebook, padding=8)
        for tab in (look, color, motion, window):
            tab.columnconfigure(1, weight=1)

        notebook.add(look, text=" Look ")
        notebook.add(color, text=" Color ")
        notebook.add(motion, text=" Motion ")
        notebook.add(window, text=" Window ")

        self._build_look(look)
        self._build_color(color)
        self._build_motion(motion)
        self._build_window(window)

        ttk.Label(
            outer,
            text=f"v{__version__}  ·  H hide  ·  saved next to the app",
            foreground="#777",
        ).pack(anchor="w")

        self.reload_from_store()

    def set_on_close(self, callback: Callable[[], None]) -> None:
        self._on_close = callback

    def pump(self) -> None:
        try:
            if self.root.winfo_exists():
                self.root.update()
        except tk.TclError:
            pass

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def toggle(self) -> None:
        try:
            if self.root.state() == "withdrawn":
                self.show()
            else:
                self.hide()
        except tk.TclError:
            pass

    def destroy(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _build_preset_bar(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text="Profile").pack(side="left")
        self._preset_var = tk.StringVar(value=str(self.store.get("active_profile") or "Classic"))
        self._preset_combo = ttk.Combobox(
            row,
            textvariable=self._preset_var,
            values=profile_names(self.store.snapshot()),
            state="readonly",
            width=16,
        )
        self._preset_combo.pack(side="left", padx=(6, 4), fill="x", expand=True)
        self._preset_combo.bind("<<ComboboxSelected>>", self._apply_selected_preset)
        ttk.Button(row, text="Load", width=7, command=self._apply_selected_preset).pack(side="left")

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(4, 0))
        ttk.Button(actions, text="Save as", width=9, command=self._save_profile).pack(side="left")
        self._rename_btn = ttk.Button(actions, text="Rename", width=9, command=self._rename_profile)
        self._rename_btn.pack(side="left", padx=(4, 0))
        self._delete_btn = ttk.Button(actions, text="Delete", width=9, command=self._delete_profile)
        self._delete_btn.pack(side="left", padx=(4, 0))
        self._sync_profile_buttons()

    def _hint(self, parent: ttk.Frame, row: int, text: str) -> None:
        ttk.Label(parent, text=text, foreground="#777").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )

    def _slider(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        key: str,
        from_: float,
        to: float,
        resolution: float,
        fmt: str = "{:.2f}",
        as_int: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
        var = tk.DoubleVar(value=float(self.store.get(key)))
        self._vars[key] = var
        value_label = ttk.Label(parent, width=5, anchor="e")

        def on_change(_value: str | None = None) -> None:
            raw = float(var.get())
            if resolution >= 1:
                raw = round(raw / resolution) * resolution
            if as_int:
                raw = int(round(raw))
            value_label.configure(text=fmt.format(raw))
            if not self._loading:
                self.store.update(**{key: raw})

        ttk.Scale(parent, from_=from_, to=to, variable=var, command=on_change).grid(
            row=row, column=1, sticky="ew", pady=1
        )
        value_label.grid(row=row, column=2, sticky="e", padx=(4, 0))
        self._value_labels[key] = (value_label, fmt)
        on_change()

    def _int_box(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        key: str,
        lo: int,
        hi: int,
        suffix: str = "",
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
        var = tk.StringVar(value=str(int(self.store.get(key))))
        self._vars[key] = var

        def commit(_event: object | None = None) -> None:
            if self._loading:
                return
            try:
                value = int(round(float(var.get())))
            except ValueError:
                var.set(str(int(self.store.get(key))))
                return
            value = max(lo, min(hi, value))
            var.set(str(value))
            self.store.update(**{key: value})

        box = ttk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=7, command=commit)
        box.grid(row=row, column=1, sticky="w", pady=1)
        box.bind("<Return>", commit)
        box.bind("<FocusOut>", commit)
        ttk.Label(parent, text=suffix or f"{lo}–{hi}", foreground="#777").grid(row=row, column=2, sticky="e")

    def _choice(self, parent: ttk.Frame, row: int, label: str, key: str, options: list[str], width: int = 12) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
        var = tk.StringVar(value=str(self.store.get(key)))
        self._vars[key] = var
        combo = ttk.Combobox(parent, textvariable=var, values=options, state="readonly", width=width)
        combo.grid(row=row, column=1, columnspan=2, sticky="w", pady=1)

        def on_change(_event: object | None = None) -> None:
            if not self._loading:
                self.store.update(**{key: var.get()})

        combo.bind("<<ComboboxSelected>>", on_change)

    def _toggle(self, parent: ttk.Frame, row: int, label: str, key: str, column: int = 0, span: int = 3) -> None:
        var = tk.BooleanVar(value=bool(self.store.get(key)))
        self._vars[key] = var
        ttk.Checkbutton(
            parent,
            text=label,
            variable=var,
            command=lambda: None if self._loading else self.store.update(**{key: bool(var.get())}),
        ).grid(row=row, column=column, columnspan=span, sticky="w", pady=1)

    def _color_row(self, parent: ttk.Frame, row: int, label: str, key: str) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
        holder = ttk.Frame(parent)
        holder.grid(row=row, column=1, columnspan=2, sticky="ew", pady=1)
        channels = []
        current = list(self.store.get(key))
        for i in range(3):
            var = tk.DoubleVar(value=float(current[i]))
            channels.append(var)
            ttk.Scale(
                holder,
                from_=0,
                to=255,
                variable=var,
                command=lambda _v, k=key: self._sync_color(k),
                length=70,
            ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        preview = tk.Label(holder, width=3, relief="solid", borderwidth=1, cursor="hand2")
        preview.pack(side="right", ipady=3, ipadx=2)
        preview.bind("<Button-1>", lambda _e, k=key: self._pick_color(k))
        self._color_previews[key] = preview
        self._vars[key] = channels  # type: ignore[assignment]
        self._paint_color(key)

    def _sync_color(self, key: str) -> None:
        vars_ = self._vars[key]
        color = [max(0, min(255, int(round(float(v.get()))))) for v in vars_]
        self._paint_color(key)
        if not self._loading:
            self.store.update(**{key: color})

    def _paint_color(self, key: str) -> None:
        vars_ = self._vars[key]
        color = [max(0, min(255, int(round(float(v.get()))))) for v in vars_]
        self._color_previews[key].configure(background="#{:02x}{:02x}{:02x}".format(*color))

    def _pick_color(self, key: str) -> None:
        vars_ = self._vars[key]
        current = "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(round(float(v.get()))))) for v in vars_])
        picked = colorchooser.askcolor(color=current, parent=self.root, title=key.replace("_", " "))
        if not picked or not picked[0]:
            return
        rgb = [int(c) for c in picked[0]]
        self._loading = True
        for var, value in zip(vars_, rgb):
            var.set(value)
        self._loading = False
        self._sync_color(key)

    def _build_look(self, parent: ttk.Frame) -> None:
        self._choice(parent, 0, "Trail", "trail_style", STYLES)
        self._slider(parent, 1, "Thickness", "thickness", 0.5, 20, 0.1)
        self._slider(parent, 2, "Taper", "taper", 0, 1, 0.01)
        self._slider(parent, 3, "Length", "line_length", 8, 400, 1, "{:.0f}", as_int=True)
        self._slider(parent, 4, "Lifetime", "trail_lifetime", 0, 8, 0.05, "{:.2f}")
        self._hint(parent, 5, "Wait, cut the oldest point, timer restarts. 0 = length only.")
        self._slider(parent, 6, "Fade", "fade", 0, 1, 0.01)
        self._slider(parent, 7, "Glow", "glow", 0, 1, 0.01)
        self._slider(parent, 8, "Opacity", "opacity", 0.05, 1, 0.01)
        self._slider(parent, 9, "Fringe", "outline", 0, 8, 0.1)
        self._color_row(parent, 10, "Fringe color", "outline_color")
        self._hint(parent, 11, "Black fringe by default. 0 turns the outline off.")
        self._slider(parent, 12, "Crosshair size", "cursor_size", 0, 28, 0.1)
        self._int_box(parent, 13, "Angle", "cursor_angle", 0, 359, "0=+  45=×")
        self._toggle(parent, 14, "Match trail color", "cursor_follow_color")

    def _build_color(self, parent: ttk.Frame) -> None:
        self._choice(parent, 0, "Mode", "color_mode", MODES)
        self._hint(parent, 1, "Rainbow: green ends. Velocity: hue from speed. Magenta skipped for OBS.")
        self._color_row(parent, 2, "Line", "line_color")
        self._color_row(parent, 3, "Cursor", "head_color")
        self._color_row(parent, 4, "Tail", "tail_color")
        self._slider(parent, 5, "End / slow", "hue_min", 0, 360, 1, "{:.0f}", as_int=True)
        self._slider(parent, 6, "Fast hue", "hue_max", 0, 360, 1, "{:.0f}", as_int=True)
        self._slider(parent, 7, "Rainbow span", "hue_span", 0, 360, 1, "{:.0f}", as_int=True)
        self._color_row(parent, 8, "Background", "bg_color")
        self._toggle(parent, 9, "Chroma magenta (OBS Color Key)", "use_chroma")
        ttk.Separator(parent).grid(row=10, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        self._toggle(parent, 11, "Particles", "particles_enabled")
        self._slider(parent, 12, "Amount", "particle_amount", 0, 40, 1, "{:.0f}", as_int=True)
        self._slider(parent, 13, "Size", "particle_size", 0.5, 8, 0.1)
        self._slider(parent, 14, "Lifetime", "particle_lifetime", 0.05, 1.5, 0.01)
        self._toggle(parent, 15, "Particles match trail", "particle_follow_color")
        self._color_row(parent, 16, "Particle", "particle_color")

    def _build_motion(self, parent: ttk.Frame) -> None:
        self._slider(parent, 0, "Weight", "tracking_weight", 1, 200, 1, "{:.0f}", as_int=True)
        self._hint(parent, 1, "50 = a hard swipe fills this window.")
        self._choice(parent, 2, "View", "view_mode", VIEW_MODES)
        self._hint(parent, 3, "Map: cursor stays centered, the world scrolls under it.")
        self._slider(parent, 4, "Inertia", "inertia", 0, 0.95, 0.01)
        self._slider(parent, 5, "Wall ease", "edge_spring", 0, 1.0, 0.01)
        self._hint(parent, 6, "Window view only. 0 = hard edges. Map has no walls.")
        self._slider(parent, 7, "Sensitivity", "sensitivity", 0.1, 3.0, 0.05)
        self._int_box(parent, 8, "Capture FPS", "capture_fps", 1, 240, "mouse + trail")
        self._hint(parent, 9, "Type any FPS. Trail updates that many times per second.")

    def _build_window(self, parent: ttk.Frame) -> None:
        self._toggle(parent, 0, "OBS mode (borderless + chroma + click-through)", "obs_mode")
        self._hint(parent, 1, "Hold Alt to drag the window. It stays on the taskbar.")
        self._slider(parent, 2, "Height", "window_size", 256, 1024, 16, "{:.0f}", as_int=True)
        self._choice(parent, 3, "Ratio", "window_ratio", RATIO_CHOICES, width=12)
        self._hint(parent, 4, "Monitor follows the display your mouse is on.")
        ttk.Label(parent, text="Custom").grid(row=5, column=0, sticky="w", padx=(0, 6), pady=1)
        pair = ttk.Frame(parent)
        pair.grid(row=5, column=1, columnspan=2, sticky="w", pady=1)
        self._mini_int(pair, "window_ratio_w", 1, 64)
        ttk.Label(pair, text=":").pack(side="left", padx=4)
        self._mini_int(pair, "window_ratio_h", 1, 64)
        ttk.Label(parent, text="W:H when Ratio is Custom", foreground="#777").grid(
            row=6, column=1, columnspan=2, sticky="w"
        )
        self._toggle(parent, 7, "Always on top", "always_on_top")
        self._toggle(parent, 8, "Borderless (when OBS mode is off)", "borderless")
        self._toggle(parent, 9, "Show click count", "show_clicks")
        self._slider(parent, 10, "Font size", "font_size", 10, 48, 1, "{:.0f}", as_int=True)
        self._color_row(parent, 11, "Counter", "counter_color")
        ttk.Separator(parent).grid(row=12, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        self._toggle(parent, 13, "Stats in this window", "show_perf")
        self._toggle(parent, 14, "Stats on the tracker (shows in OBS)", "show_perf_overlay")
        self._perf_var = tk.StringVar(value="Turn on stats to see capture FPS, CPU, RAM")
        ttk.Label(parent, textvariable=self._perf_var, justify="left", font=("Consolas", 9)).grid(
            row=15, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

    def _mini_int(self, parent: ttk.Frame, key: str, lo: int, hi: int) -> None:
        var = tk.StringVar(value=str(int(self.store.get(key))))
        self._vars[key] = var

        def commit(_event: object | None = None) -> None:
            if self._loading:
                return
            try:
                value = int(round(float(var.get())))
            except ValueError:
                var.set(str(int(self.store.get(key))))
                return
            value = max(lo, min(hi, value))
            var.set(str(value))
            self.store.update(**{key: value})

        box = ttk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=5, command=commit)
        box.pack(side="left")
        box.bind("<Return>", commit)
        box.bind("<FocusOut>", commit)

    def set_perf_text(self, text: str) -> None:
        if getattr(self, "_perf_var", None) is None:
            return
        try:
            self._perf_var.set(text)
        except tk.TclError:
            pass

    def _sync_profile_buttons(self) -> None:
        custom = not is_builtin_profile(self._preset_var.get())
        state = "normal" if custom else "disabled"
        if getattr(self, "_rename_btn", None) is not None:
            self._rename_btn.configure(state=state)
            self._delete_btn.configure(state=state)

    def _refresh_profile_combo(self, selected: str | None = None) -> None:
        names = profile_names(self.store.snapshot())
        self._preset_combo.configure(values=names)
        pick = selected or str(self.store.get("active_profile") or "Classic")
        if pick not in names:
            pick = "Classic"
        self._preset_var.set(pick)
        self._sync_profile_buttons()

    def _ask_profile_name(self, title: str, prompt: str, initial: str = "") -> str | None:
        name = simpledialog.askstring(title, prompt, initialvalue=initial, parent=self.root)
        if name is None:
            return None
        name = sanitize_profile_name(name)
        if not name:
            messagebox.showerror(title, "Enter a name.", parent=self.root)
            return None
        if is_builtin_profile(name):
            messagebox.showerror(title, f'"{name}" is a built-in look. Choose another name.', parent=self.root)
            return None
        return name

    def _apply_selected_preset(self, _event: object | None = None) -> None:
        name = self._preset_var.get()
        self.store.replace(apply_profile(self.store.snapshot(), name))
        self.reload_from_store(keep_preset=name)

    def _save_profile(self) -> None:
        current = self._preset_var.get()
        initial = "" if is_builtin_profile(current) else current
        name = self._ask_profile_name("Save profile", "Name this look:", initial)
        if name is None:
            return
        existing = self.store.get("profiles") or {}
        if name in existing and not messagebox.askyesno(
            "Save profile", f'Overwrite "{name}"?', parent=self.root
        ):
            return
        try:
            saved = self.store.save_profile(name)
        except ValueError as exc:
            messagebox.showerror("Save profile", str(exc), parent=self.root)
            return
        self._refresh_profile_combo(saved)

    def _rename_profile(self) -> None:
        old = self._preset_var.get()
        if is_builtin_profile(old):
            return
        name = self._ask_profile_name("Rename profile", "New name:", old)
        if name is None or name == old:
            return
        existing = self.store.get("profiles") or {}
        if name in existing:
            messagebox.showerror("Rename profile", f'A profile named "{name}" already exists.', parent=self.root)
            return
        try:
            renamed = self.store.rename_profile(old, name)
        except ValueError as exc:
            messagebox.showerror("Rename profile", str(exc), parent=self.root)
            return
        self._refresh_profile_combo(renamed)

    def _delete_profile(self) -> None:
        name = self._preset_var.get()
        if is_builtin_profile(name):
            return
        if not messagebox.askyesno(
            "Delete profile",
            f'Delete "{name}"? This cannot be undone.',
            parent=self.root,
        ):
            return
        try:
            next_name = self.store.delete_profile(name)
        except ValueError as exc:
            messagebox.showerror("Delete profile", str(exc), parent=self.root)
            return
        self.reload_from_store(keep_preset=next_name)

    def reload_from_store(self, keep_preset: str | None = None) -> None:
        self._loading = True
        data = self.store.snapshot()
        for key, var in self._vars.items():
            value = data.get(key)
            if isinstance(var, list):
                for i, channel in enumerate(var):
                    channel.set(int(value[i]))
                self._paint_color(key)
            elif isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(var, tk.StringVar):
                var.set(str(value))
            else:
                var.set(float(value))
        for key, (label, fmt) in self._value_labels.items():
            label.configure(text=fmt.format(float(self._vars[key].get())))
        self._refresh_profile_combo(keep_preset or str(data.get("active_profile") or "Classic"))
        self._loading = False
