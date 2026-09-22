from __future__ import annotations

import os
import time
import ctypes
from ctypes import Structure, byref, sizeof, windll, wintypes


class _FILETIME(Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _PROCESS_MEMORY_COUNTERS(Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _filetime_u64(ft: _FILETIME) -> int:
    return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)


class PerfMonitor:
    def __init__(self) -> None:
        self.target_fps = 60
        self.actual_fps = 0.0
        self.update_ms = 0.0
        self.cpu_percent = 0.0
        self.ram_mb = 0.0
        self.trail_points = 0
        self._cpus = max(os.cpu_count() or 1, 1)
        self._kernel32 = windll.kernel32
        self._process = self._kernel32.GetCurrentProcess()
        self._last_proc = 0
        self._last_wall = time.perf_counter()
        self._last_capture = 0.0
        self._work_start = 0.0
        self._fps_ema = 0.0
        self._kernel32.K32GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self._kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
        self._read_ram()

    def begin_update(self) -> None:
        self._work_start = time.perf_counter()

    def end_update(self, target_fps: int, trail_n: int) -> None:
        now = time.perf_counter()
        self.target_fps = target_fps
        self.update_ms = (now - self._work_start) * 1000.0
        self.trail_points = trail_n
        if self._last_capture > 0:
            instant = 1.0 / max(now - self._last_capture, 1e-6)
            self._fps_ema = instant if self._fps_ema == 0 else self._fps_ema * 0.8 + instant * 0.2
            self.actual_fps = self._fps_ema
        self._last_capture = now
        if now - self._last_wall >= 0.4:
            self._refresh_process(now)

    def _read_ram(self) -> None:
        mem = _PROCESS_MEMORY_COUNTERS()
        mem.cb = sizeof(_PROCESS_MEMORY_COUNTERS)
        if self._kernel32.K32GetProcessMemoryInfo(self._process, byref(mem), mem.cb):
            self.ram_mb = mem.WorkingSetSize / (1024 * 1024)

    def _refresh_process(self, now: float) -> None:
        creation = _FILETIME()
        exit_t = _FILETIME()
        kernel = _FILETIME()
        user = _FILETIME()
        if self._kernel32.GetProcessTimes(
            self._process, byref(creation), byref(exit_t), byref(kernel), byref(user)
        ):
            proc = _filetime_u64(kernel) + _filetime_u64(user)
            wall = now - self._last_wall
            if self._last_proc and wall > 0:
                proc_sec = (proc - self._last_proc) / 10_000_000
                self.cpu_percent = max(0.0, min(100.0 * proc_sec / wall / self._cpus, 100.0))
            self._last_proc = proc
            self._last_wall = now
        self._read_ram()

    def text(self) -> str:
        return (
            f"Capture FPS   {self.target_fps:>3} set    {self.actual_fps:5.1f} actual\n"
            f"Update        {self.update_ms:5.2f} ms\n"
            f"CPU           {self.cpu_percent:5.1f} %\n"
            f"RAM           {self.ram_mb:5.1f} MB\n"
            f"Trail         {self.trail_points:>3} pts"
        )
