# Mouse Tracker

A portable Windows mouse trail for OBS. It does **not** draw a mini map of your desktop. Relative mouse movement is mapped into a window, so the scribble stays on-screen no matter where the real cursor goes.

## Disclaimer

Yes, this is AI-generated code. Nothing available with source had the configuration options I wanted; this does the job. Do what you will with the project.

## Download

Download `MouseTracker.exe` from [Releases](../../releases). No Python required.

## OBS setup

1. Run `MouseTracker.exe`. Two windows open: **Mouse Tracker** (the square) and **Mouse Tracker Settings**.
2. In OBS, add a **Window Capture** source and pick `Mouse Tracker`.
3. Crop off the title bar if you want a clean square (`Alt` drag the source bounds, or use Crop).
4. For a transparent overlay, enable **Use chroma magenta** in settings, then add a **Color Key** filter on the source (`#FF00FF`).
5. Place it on the canvas — corner, under cam, wherever.

`config.json` is created next to the exe on first run. Your look and saved profiles travel with the file. Copy the exe to another folder and it starts fresh.

## Profiles

Built-in looks: **Classic**, **Neon**, **Rainbow**, **Phosphor**, **Ink**. These are starting points; keep tweaking.

- **Load** — apply the selected look.
- **Save as** — store the current mix under a name. Overwrite if that name already exists.
- **Rename** / **Delete** — custom profiles only. Built-ins stay put.

An older single **Custom** slot is imported automatically as a profile named `Custom`.

## Settings

Live sliders. Changes save next to the app; nothing waits for a restart.

- **Trail** — line / ribbon / dots, thickness, taper (fat at the cursor, thin at the tail), **lifetime** (wait this long, cut the oldest point, restart the timer; `0` keeps length-only), fade (opacity along what is left), glow, fringe.
- **Crosshair** — size and angle (`0` = `+`, `45` = `×`). Size `0` hides it. Color can match the trail or stay fixed.
- **Color** — solid, rainbow (same hue at both ends, spectrum in the middle), velocity (color from how fast you flick), or age (head → tail RGB). Rainbow/velocity skip magenta so OBS Color Key `#FF00FF` does not eat the trail.
- **Motion** — tracking weight, inertia, edge spring, sensitivity, **Capture FPS** (1–240). Mouse and trail update that many times per second — match your OBS source.
- **Window** — **OBS mode** is on by default (borderless + chroma magenta, click-through so it cannot eat game clicks). Hold **Alt** and drag to move the square. Turn OBS mode off for a normal window.
- **Performance debug** — capture FPS set vs actual, update time, CPU, RAM. Optional overlay on the square (that one *will* show up in OBS).
- **Particles** — optional wake. Off by default.

Hotkeys on the square window: `Esc` quit, `C` clear trail, `H` hide/show settings.

## Run from source

Python 3.11+ on Windows.

```powershell
git clone https://github.com/<you>/MouseTracker.git
cd MouseTracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

```powershell
python -m unittest discover -s tests -v
```

## Build the exe

```powershell
pyinstaller MouseTracker.spec --noconfirm
```

The binary lands in `dist\MouseTracker.exe`. GitHub Actions builds the same file on tags named `v*` (for example `v0.2.0`) and attaches it to the release.

## Layout

```
main.py                 entry point
tracker/config.py       defaults, presets, named profiles, config.json
tracker/settings_ui.py  Tk settings window
tracker/render.py       trail, crosshair, particles
tracker/physics.py      virtual cursor and trail points
tracker/mouse.py        raw mouse input
tracker/win32.py        overlay, DPI, raw input
```