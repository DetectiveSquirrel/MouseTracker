from __future__ import annotations

import ctypes
from ctypes import wintypes

import pygame

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
GWL_EXSTYLE = -20
GWL_HWNDPARENT = -8
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_MENU = 0x12
LWA_ALPHA = 0x02

_user32 = ctypes.windll.user32
_winmm = ctypes.windll.winmm
_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short
_user32.GetWindowLongPtrW.restype = ctypes.c_void_p
_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_user32.SetWindowLongPtrW.restype = ctypes.c_void_p
_user32.GetRawInputData.argtypes = [
    wintypes.HANDLE,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT),
    wintypes.UINT,
]
_user32.GetRawInputData.restype = wintypes.UINT
_user32.RegisterRawInputDevices.argtypes = [
    ctypes.c_void_p,
    wintypes.UINT,
    wintypes.UINT,
]
_user32.RegisterRawInputDevices.restype = wintypes.BOOL
_user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
_user32.DefWindowProcW.restype = ctypes.c_ssize_t


def _exstyle(hwnd: int) -> int:
    return int(_user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE) or 0)


def _set_exstyle(hwnd: int, style: int) -> None:
    _user32.SetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)


def set_timer_resolution(ms: int) -> None:
    """1ms scheduler for high-rate mouse polling. Pass 0 to restore."""
    try:
        if ms <= 0:
            _winmm.timeEndPeriod(1)
        else:
            _winmm.timeBeginPeriod(max(ms, 1))
    except (AttributeError, OSError):
        pass


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    try:
        _user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def _hwnd() -> int | None:
    info = pygame.display.get_wm_info()
    handle = info.get("window")
    return int(handle) if handle else None


def set_always_on_top(enabled: bool) -> None:
    hwnd = _hwnd()
    if not hwnd:
        return
    _user32.SetWindowPos(
        wintypes.HWND(hwnd),
        wintypes.HWND(HWND_TOPMOST if enabled else HWND_NOTOPMOST),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def configure_overlay(click_through: bool) -> None:
    """Click-through overlay that still shows on the taskbar as Mouse Tracker."""
    hwnd = _hwnd()
    if not hwnd:
        return
    # Un-own from any parent (tk) so Windows gives this window its own taskbar button.
    _user32.SetWindowLongPtrW(wintypes.HWND(hwnd), GWL_HWNDPARENT, 0)
    style = _exstyle(hwnd)
    style |= WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_APPWINDOW
    style &= ~WS_EX_TOOLWINDOW
    if click_through:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
    _set_exstyle(hwnd, style)
    _user32.SetLayeredWindowAttributes(wintypes.HWND(hwnd), 0, 255, LWA_ALPHA)
    _user32.SetWindowPos(
        wintypes.HWND(hwnd),
        wintypes.HWND(0),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED,
    )


def key_down(vk: int) -> bool:
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def window_position() -> tuple[int, int]:
    hwnd = _hwnd()
    if not hwnd:
        return (0, 0)
    rect = wintypes.RECT()
    _user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return int(rect.left), int(rect.top)


def move_window(x: int, y: int) -> None:
    hwnd = _hwnd()
    if not hwnd:
        return
    _user32.SetWindowPos(
        wintypes.HWND(hwnd),
        wintypes.HWND(0),
        int(x),
        int(y),
        0,
        0,
        SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def cursor_position() -> tuple[int, int]:
    point = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


_MONITOR_DEFAULTTONEAREST = 2
_user32.MonitorFromPoint.restype = wintypes.HMONITOR


def cursor_monitor_size() -> tuple[int, int]:
    """Pixel size of the monitor the cursor is on (the space we scale into the window)."""
    x, y = cursor_position()
    monitor = _user32.MonitorFromPoint(wintypes.POINT(x, y), _MONITOR_DEFAULTTONEAREST)
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not _user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        w = int(_user32.GetSystemMetrics(0)) or 1920
        h = int(_user32.GetSystemMetrics(1)) or 1080
        return w, h
    width = int(info.rcMonitor.right - info.rcMonitor.left)
    height = int(info.rcMonitor.bottom - info.rcMonitor.top)
    return max(width, 1), max(height, 1)


def show_error(title: str, message: str) -> None:
    _user32.MessageBoxW(None, message, title, 0x10)


WM_INPUT = 0x00FF
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
RIDEV_INPUTSINK = 0x00000100
RIDEV_REMOVE = 0x00000001
MOUSE_MOVE_ABSOLUTE = 0x01
HWND_MESSAGE = wintypes.HWND(-3)
_WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class _RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class _RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class _RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("ulButtons", wintypes.ULONG),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class _RAWINPUT(ctypes.Structure):
    _fields_ = [
        ("header", _RAWINPUTHEADER),
        ("mouse", _RAWMOUSE),
    ]


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class RawInputListener:
    """Listen-only relative mouse, same data games use. No hook, no capture."""

    def __init__(self) -> None:
        self._hwnd = None
        self._on_move = None
        self._wndproc = _WNDPROC(self._wnd_proc)
        self._class = "MouseTrackerRawInput"

    def start(self, on_move) -> bool:
        self._on_move = on_move
        hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinstance
        wc.lpszClassName = self._class
        if not _user32.RegisterClassExW(ctypes.byref(wc)):
            err = ctypes.GetLastError()
            if err not in {1410, 0}:  # already registered
                return False
        hwnd = _user32.CreateWindowExW(
            0,
            self._class,
            "MouseTrackerRaw",
            0,
            0,
            0,
            0,
            0,
            HWND_MESSAGE,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            return False
        self._hwnd = hwnd
        if not self._register(hwnd):
            _user32.DestroyWindow(wintypes.HWND(hwnd))
            self._hwnd = None
            return False
        return True

    def _register(self, hwnd: int) -> bool:
        device = _RAWINPUTDEVICE(1, 2, RIDEV_INPUTSINK, wintypes.HWND(hwnd))
        return bool(_user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(_RAWINPUTDEVICE)))

    def pump(self) -> None:
        msg = wintypes.MSG()
        while _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self) -> None:
        if self._hwnd:
            device = _RAWINPUTDEVICE(1, 2, RIDEV_REMOVE, None)
            _user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(_RAWINPUTDEVICE))
            _user32.DestroyWindow(wintypes.HWND(self._hwnd))
            self._hwnd = None
        self._on_move = None

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            self._read_raw(lparam)
            return 0
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _read_raw(self, handle) -> None:
        handle = handle & 0xFFFFFFFFFFFFFFFF
        size = wintypes.UINT(0)
        _user32.GetRawInputData(handle, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(_RAWINPUTHEADER))
        if size.value == 0:
            return
        buf = ctypes.create_string_buffer(size.value)
        got = _user32.GetRawInputData(handle, RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(_RAWINPUTHEADER))
        if got == 0xFFFFFFFF or got == 0:
            return
        data = _RAWINPUT.from_buffer_copy(buf)
        if data.header.dwType != RIM_TYPEMOUSE:
            return
        if data.mouse.usFlags & MOUSE_MOVE_ABSOLUTE:
            return
        dx, dy = int(data.mouse.lLastX), int(data.mouse.lLastY)
        if (dx or dy) and self._on_move:
            self._on_move(dx, dy)
