from __future__ import annotations

import atexit
import ctypes
from ctypes import wintypes
import math
import os
import re
import signal
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageFont


APP_TITLE = "FocusTool"
HOSTS_PATH = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
START_MARKER = "# >>> FocusTool managed block >>>"
END_MARKER = "# <<< FocusTool managed block <<<"

BLOCKED_DOMAINS = [
    "zhihu.com",
    "www.zhihu.com",
    "m.zhihu.com",
    "zhuanlan.zhihu.com",
    "api.zhihu.com",
    "static.zhihu.com",
    "zhimg.com",
    "www.zhimg.com",
    "picx.zhimg.com",
    "pic1.zhimg.com",
    "pic2.zhimg.com",
    "pic3.zhimg.com",
    "pic4.zhimg.com",
    "bilibili.com",
    "www.bilibili.com",
    "m.bilibili.com",
    "space.bilibili.com",
    "search.bilibili.com",
    "t.bilibili.com",
    "live.bilibili.com",
    "api.bilibili.com",
    "api.vc.bilibili.com",
    "b23.tv",
    "www.b23.tv",
    "biliapi.net",
    "biliapi.com",
    "bilivideo.com",
    "bilibili.tv",
]

TRANSPARENT_COLOR = "#010203"
TEXT_COLOR = "#ffffff"
FONT_SIZE = 48
PADDING_X = 14
PADDING_Y = 8
MAX_SECONDS = 360 * 60
TEXT_ALPHA = 160
STROKE_ALPHA = 45
OVERLAY_Y_RATIO = 0.08
BLOCKED_HOST_IPS = {"0.0.0.0", "127.0.0.1", "::1"}

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_TIMER = 0x0113
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
DIB_RGB_COLORS = 0
BI_RGB = 0
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x00000102
SYNCHRONIZE = 0x00100000
FILE_ATTRIBUTE_READONLY = 0x00000001
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
ERROR_ALREADY_EXISTS = 183


def configure_win32_prototypes() -> None:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    user32.LoadCursorW.restype = ctypes.c_void_p
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.RegisterClassExW.restype = ctypes.c_uint16
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEX)]
    user32.CreateWindowExW.restype = ctypes.c_void_p
    user32.CreateWindowExW.argtypes = [
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.GetDC.restype = ctypes.c_void_p
    user32.GetDC.argtypes = [ctypes.c_void_p]
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.SetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    user32.SetWindowPos.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.UpdateLayeredWindow.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(POINT),
        ctypes.POINTER(SIZE),
        ctypes.c_void_p,
        ctypes.POINTER(POINT),
        ctypes.c_uint32,
        ctypes.POINTER(BLENDFUNCTION),
        ctypes.c_uint32,
    ]
    gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
    gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    gdi32.CreateDIBSection.restype = ctypes.c_void_p
    gdi32.CreateDIBSection.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    gdi32.SelectObject.restype = ctypes.c_void_p
    gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    gdi32.DeleteDC.argtypes = [ctypes.c_void_p]


def set_dpi_awareness() -> None:
    configure_win32_prototypes()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FocusTool.Timer")
    except Exception:
        pass


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(args: list[str] | None = None) -> bool:
    args = sys.argv[1:] if args is None else args
    if getattr(sys, "frozen", False):
        executable = sys.executable
        parameters = subprocess.list2cmdline(args)
    else:
        executable = sys.executable
        script = str(Path(__file__).resolve())
        parameters = subprocess.list2cmdline([script, *args])

    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, parameters, None, 1)
    return result > 32


class SingleInstance:
    def __init__(self) -> None:
        self.handle = None

    def acquire(self) -> bool:
        self.handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\FocusToolSingleInstance")
        return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


class HostBlocker:
    def __init__(self, path: Path = HOSTS_PATH) -> None:
        self.path = path
        self._restored = False

    def apply(self) -> None:
        text, encoding, newline = self._read_hosts()
        text = self._remove_managed_blocks(text, newline)
        text = self._remove_blocked_domain_lines(text)
        block = self._build_block(newline)
        separator = "" if not text or text.endswith(("\n", "\r")) else newline
        self._write_hosts(text + separator + block, encoding)
        self._restored = False
        flush_dns()

    def restore(self) -> None:
        if self._restored:
            return
        text, encoding, newline = self._read_hosts()
        cleaned = self._remove_managed_blocks(text, newline)
        cleaned = self._remove_blocked_domain_lines(cleaned)
        if cleaned != text:
            self._write_hosts(cleaned, encoding)
            flush_dns()
        self._restored = True

    def _read_hosts(self) -> tuple[str, str, str]:
        data = self.path.read_bytes()
        encodings = ("utf-8-sig", "utf-8", "mbcs") if data.startswith(b"\xef\xbb\xbf") else ("utf-8", "mbcs")
        for encoding in encodings:
            try:
                text = data.decode(encoding)
                newline = "\r\n" if "\r\n" in text else "\n"
                return text, encoding, newline
            except UnicodeDecodeError:
                continue
        text = data.decode("utf-8", errors="replace")
        newline = "\r\n" if "\r\n" in text else "\n"
        return text, "utf-8", newline

    def _write_hosts(self, text: str, encoding: str) -> None:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(self.path))
        was_readonly = attrs != INVALID_FILE_ATTRIBUTES and bool(attrs & FILE_ATTRIBUTE_READONLY)
        if was_readonly:
            ctypes.windll.kernel32.SetFileAttributesW(str(self.path), attrs & ~FILE_ATTRIBUTE_READONLY)
        try:
            self.path.write_text(text, encoding=encoding, newline="")
        finally:
            if was_readonly:
                ctypes.windll.kernel32.SetFileAttributesW(str(self.path), attrs)

    def _build_block(self, newline: str) -> str:
        lines = [
            START_MARKER,
            "# Zhihu and Bilibili are blocked while FocusTool is running.",
        ]
        for domain in BLOCKED_DOMAINS:
            lines.append(f"0.0.0.0 {domain}")
            lines.append(f"::1 {domain}")
        lines.append(END_MARKER)
        return newline.join(lines) + newline

    def _remove_managed_blocks(self, text: str, newline: str) -> str:
        while True:
            start = text.find(START_MARKER)
            if start == -1:
                return text
            end = text.find(END_MARKER, start)
            if end == -1:
                return text

            remove_end = end + len(END_MARKER)
            if text[remove_end : remove_end + 2] == "\r\n":
                remove_end += 2
            elif text[remove_end : remove_end + 1] in ("\n", "\r"):
                remove_end += 1

            before = text[:start]
            after = text[remove_end:]
            joiner = newline if before.strip() and after.strip() else ""
            text = before + joiner + after

    def _remove_blocked_domain_lines(self, text: str) -> str:
        blocked = {domain.lower() for domain in BLOCKED_DOMAINS}
        kept_lines = []
        for line in text.splitlines(keepends=True):
            content = line.split("#", 1)[0].strip()
            parts = content.split()
            if len(parts) >= 2 and parts[0].lower() in BLOCKED_HOST_IPS:
                hosts = {part.lower().rstrip(".") for part in parts[1:]}
                if hosts & blocked:
                    continue
            kept_lines.append(line)
        return "".join(kept_lines)


def flush_dns() -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def parse_duration(raw: str) -> int:
    text = raw.strip().lower()
    if not text:
        raise ValueError("\u8bf7\u8f93\u5165\u4e13\u6ce8\u65f6\u95f4\u3002")

    replacements = {
        "\uff1a": ":",
        "\u5c0f\u65f6": "h",
        "\u65f6": "h",
        "\u5206\u949f": "m",
        "\u5206": "m",
        "\u79d2\u949f": "s",
        "\u79d2": "s",
        "\u3000": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", "", text)

    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            minutes, seconds = _parse_clock_parts(parts)
            total = minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = _parse_clock_parts(parts)
            total = hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError("\u65f6\u95f4\u683c\u5f0f\u4e0d\u6b63\u786e\u3002")
        return _validate_duration(total)

    unit_matches = re.findall(r"(\d+(?:\.\d+)?)([hms])", text)
    if unit_matches:
        rebuilt = "".join(number + unit for number, unit in unit_matches)
        if rebuilt != text:
            raise ValueError("\u65f6\u95f4\u683c\u5f0f\u4e0d\u6b63\u786e\u3002")
        total = 0.0
        for number, unit in unit_matches:
            total += float(number) * {"h": 3600, "m": 60, "s": 1}[unit]
        return _validate_duration(round(total))

    try:
        return _validate_duration(round(float(text) * 60))
    except ValueError as exc:
        raise ValueError("\u65f6\u95f4\u683c\u5f0f\u4e0d\u6b63\u786e\u3002") from exc


def _parse_clock_parts(parts: list[str]) -> list[int]:
    values = []
    for part in parts:
        if not part.isdigit():
            raise ValueError("\u65f6\u95f4\u683c\u5f0f\u4e0d\u6b63\u786e\u3002")
        values.append(int(part))
    if len(values) >= 2 and any(value >= 60 for value in values[-2:]):
        raise ValueError("\u5206\u949f\u548c\u79d2\u6570\u5e94\u5c0f\u4e8e 60\u3002")
    return values


def _validate_duration(seconds: int) -> int:
    if seconds <= 0:
        raise ValueError("\u4e13\u6ce8\u65f6\u95f4\u5fc5\u987b\u5927\u4e8e 0\u3002")
    if seconds > MAX_SECONDS:
        raise ValueError("\u5355\u6b21\u4e13\u6ce8\u65f6\u95f4\u6700\u591a 360 \u5206\u949f\u3002")
    return seconds


def ask_duration() -> int | None:
    root = tk.Tk()
    root.title(APP_TITLE)
    root.resizable(False, False)
    root.attributes("-topmost", True)

    frame = ttk.Frame(root, padding=(18, 16, 18, 14))
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="\u8bf7\u8f93\u5165\u4e13\u6ce8\u65f6\u95f4\uff08\u5206\u949f\uff0c\u6700\u591a 360\uff09").grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="w",
    )
    value = tk.StringVar(value="25")
    entry = ttk.Entry(frame, textvariable=value, width=22)
    entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 4))
    ttk.Label(frame, text="\u4e5f\u53ef\u8f93\u5165 1h30m \u6216 1:30:00", foreground="#666666").grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="w",
    )
    error = ttk.Label(frame, text="", foreground="#b00020")
    error.grid(row=3, column=0, columnspan=2, sticky="w", pady=(7, 0))

    result: dict[str, int] = {}

    def submit(_event: object | None = None) -> None:
        try:
            result["seconds"] = parse_duration(value.get())
        except ValueError as exc:
            error.configure(text=str(exc))
            entry.focus_set()
            entry.select_range(0, tk.END)
            return
        root.destroy()

    def cancel() -> None:
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
    ttk.Button(buttons, text="\u53d6\u6d88", command=cancel).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="\u5f00\u59cb", command=submit).grid(row=0, column=1)

    root.bind("<Return>", submit)
    root.bind("<Escape>", lambda _event: cancel())
    root.protocol("WM_DELETE_WINDOW", cancel)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 3
    root.geometry(f"{width}x{height}+{x}+{y}")
    entry.focus_set()
    entry.select_range(0, tk.END)
    root.mainloop()
    return result.get("seconds")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]


class WNDCLASSEX(ctypes.Structure):
    pass


LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)

WNDCLASSEX._fields_ = [
    ("cbSize", ctypes.c_uint),
    ("style", ctypes.c_uint),
    ("lpfnWndProc", WNDPROC),
    ("cbClsExtra", ctypes.c_int),
    ("cbWndExtra", ctypes.c_int),
    ("hInstance", ctypes.c_void_p),
    ("hIcon", ctypes.c_void_p),
    ("hCursor", ctypes.c_void_p),
    ("hbrBackground", ctypes.c_void_p),
    ("lpszMenuName", ctypes.c_wchar_p),
    ("lpszClassName", ctypes.c_wchar_p),
    ("hIconSm", ctypes.c_void_p),
]


class CountdownOverlay:
    _class_registered = False
    _class_name = "FocusToolCountdownOverlay"
    _instances: dict[int, "CountdownOverlay"] = {}

    def __init__(self, seconds: int, cleanup) -> None:
        configure_win32_prototypes()
        self.seconds = seconds
        self.cleanup = cleanup
        self.deadline = time.monotonic() + seconds
        self.last_text = ""
        self.finished = False
        self.hwnd = None
        self.width = 1
        self.height = 1
        self.x = 0
        self.y = 0
        self._timer_id = 1
        self._font = self._load_font()
        self._register_window_class()
        self._create_window()
        self._tick()

    def run(self) -> None:
        msg = wintypes.MSG()
        user32 = ctypes.windll.user32
        while not self.finished and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _register_window_class(self) -> None:
        if CountdownOverlay._class_registered:
            return
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hinstance = kernel32.GetModuleHandleW(None)
        self._wndproc_ref = WNDPROC(self._window_proc)
        wndclass = WNDCLASSEX()
        wndclass.cbSize = ctypes.sizeof(WNDCLASSEX)
        wndclass.lpfnWndProc = self._wndproc_ref
        wndclass.hInstance = hinstance
        wndclass.hCursor = user32.LoadCursorW(None, 32512)
        wndclass.lpszClassName = self._class_name
        if not user32.RegisterClassExW(ctypes.byref(wndclass)):
            raise ctypes.WinError()
        CountdownOverlay._class_registered = True
        CountdownOverlay._wndproc_ref = self._wndproc_ref

    @staticmethod
    def _window_proc(hwnd, msg, wparam, lparam):
        instance = CountdownOverlay._instances.get(int(hwnd))
        if instance is None:
            return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        if msg == WM_TIMER:
            instance._tick()
            return 0
        if msg == WM_QUERYENDSESSION:
            instance._finish()
            return 1
        if msg == WM_ENDSESSION:
            if wparam:
                instance._finish()
            return 0
        if msg == WM_CLOSE:
            # 屏蔽所有窗口关闭请求（任务栏"关闭窗口"、Alt+F4 等），
            # 只能通过任务管理器结束进程来关闭。
            return 0
        if msg == WM_DESTROY:
            instance._finish(post_quit=False, destroy_window=False)
            ctypes.windll.user32.PostQuitMessage(0)
            return 0
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _create_window(self) -> None:
        user32 = ctypes.windll.user32
        hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        initial_text = self._format_time(self.seconds)
        image = self._render_image(initial_text)
        self.width, self.height = image.size
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        self.x = max(0, (screen_width - self.width) // 2)
        self.y = max(0, int(screen_height * OVERLAY_Y_RATIO))
        exstyle = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        style = WS_POPUP | WS_VISIBLE
        hwnd = user32.CreateWindowExW(
            exstyle,
            self._class_name,
            APP_TITLE,
            style,
            self.x,
            self.y,
            self.width,
            self.height,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()
        self.hwnd = hwnd
        CountdownOverlay._instances[int(hwnd)] = self
        user32.SetWindowTextW(hwnd, APP_TITLE)
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            self.x,
            self.y,
            self.width,
            self.height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
        self._update_layered_window(image)
        user32.SetTimer(hwnd, self._timer_id, 200, None)

    def _tick(self) -> None:
        if self.finished:
            return
        remaining = max(0, math.ceil(self.deadline - time.monotonic()))
        text = self._format_time(remaining)
        if text != self.last_text:
            self.last_text = text
            self._update_layered_window(self._render_image(text))
        if remaining <= 0:
            self._finish()

    def _finish(self, post_quit: bool = True, destroy_window: bool = True) -> None:
        if self.finished:
            return
        self.finished = True
        self.cleanup()
        user32 = ctypes.windll.user32
        if self.hwnd:
            user32.KillTimer(self.hwnd, self._timer_id)
            CountdownOverlay._instances.pop(int(self.hwnd), None)
            if destroy_window and user32.IsWindow(self.hwnd):
                user32.DestroyWindow(self.hwnd)
        if post_quit:
            user32.PostQuitMessage(0)

    def _format_time(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"

    def _load_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("IMPRISHA.TTF", "segoeuib.ttf", "seguisb.ttf", "arialbd.ttf"):
            path = fonts_dir / name
            if path.exists():
                return ImageFont.truetype(str(path), FONT_SIZE)
        return ImageFont.load_default()

    def _render_image(self, text: str) -> Image.Image:
        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), text, font=self._font, stroke_width=2)
        width = bbox[2] - bbox[0] + PADDING_X * 2
        height = bbox[3] - bbox[1] + PADDING_Y * 2
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x = PADDING_X - bbox[0]
        y = PADDING_Y - bbox[1]
        draw.text(
            (x, y),
            text,
            font=self._font,
            fill=(255, 255, 255, TEXT_ALPHA),
            stroke_width=1,
            stroke_fill=(0, 0, 0, STROKE_ALPHA),
        )
        return image

    def _update_layered_window(self, image: Image.Image) -> None:
        if not self.hwnd:
            return
        if image.size != (self.width, self.height):
            self.width, self.height = image.size
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            self.x = max(0, (screen_width - self.width) // 2)

        bgra = self._to_premultiplied_bgra(image)
        hdc_screen = ctypes.windll.user32.GetDC(None)
        hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
        bits = ctypes.c_void_p()
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.width
        bmi.bmiHeader.biHeight = -self.height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        hbitmap = ctypes.windll.gdi32.CreateDIBSection(
            hdc_screen,
            ctypes.byref(bmi),
            DIB_RGB_COLORS,
            ctypes.byref(bits),
            None,
            0,
        )
        if not hbitmap:
            ctypes.windll.gdi32.DeleteDC(hdc_mem)
            ctypes.windll.user32.ReleaseDC(None, hdc_screen)
            raise ctypes.WinError()
        ctypes.memmove(bits, bgra, len(bgra))
        old_bitmap = ctypes.windll.gdi32.SelectObject(hdc_mem, hbitmap)
        destination = POINT(self.x, self.y)
        size = SIZE(self.width, self.height)
        source = POINT(0, 0)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        ctypes.windll.user32.UpdateLayeredWindow(
            self.hwnd,
            hdc_screen,
            ctypes.byref(destination),
            ctypes.byref(size),
            hdc_mem,
            ctypes.byref(source),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )
        ctypes.windll.gdi32.SelectObject(hdc_mem, old_bitmap)
        ctypes.windll.gdi32.DeleteObject(hbitmap)
        ctypes.windll.gdi32.DeleteDC(hdc_mem)
        ctypes.windll.user32.ReleaseDC(None, hdc_screen)

    def _to_premultiplied_bgra(self, image: Image.Image) -> bytes:
        rgba = image.convert("RGBA")
        pixels = bytearray(rgba.tobytes())
        for offset in range(0, len(pixels), 4):
            red = pixels[offset]
            green = pixels[offset + 1]
            blue = pixels[offset + 2]
            alpha = pixels[offset + 3]
            pixels[offset] = blue * alpha // 255
            pixels[offset + 1] = green * alpha // 255
            pixels[offset + 2] = red * alpha // 255
        return bytes(pixels)


def show_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(APP_TITLE, message)
    root.destroy()


def show_info(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(APP_TITLE, message)
    root.destroy()


def start_restore_watchdog(parent_pid: int, restore_at_epoch: float) -> None:
    if getattr(sys, "frozen", False):
        executable = sys.executable
        args = ["--watchdog", str(parent_pid), str(restore_at_epoch)]
    else:
        executable = sys.executable
        args = [str(Path(__file__).resolve()), "--watchdog", str(parent_pid), str(restore_at_epoch)]

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [executable, *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
    except Exception:
        pass


def run_watchdog(argv: list[str]) -> int:
    configure_win32_prototypes()
    try:
        index = argv.index("--watchdog")
        parent_pid = int(argv[index + 1])
        restore_at_epoch = float(argv[index + 2])
    except (ValueError, IndexError):
        return 2

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)
    try:
        while True:
            now = time.time()
            if now >= restore_at_epoch:
                break
            wait_ms = min(1000, max(1, int((restore_at_epoch - now) * 1000)))
            if not handle:
                break
            wait_result = kernel32.WaitForSingleObject(handle, wait_ms)
            if wait_result == WAIT_OBJECT_0:
                break
            if wait_result != WAIT_TIMEOUT:
                break
        HostBlocker().restore()
        return 0
    except Exception:
        return 1
    finally:
        if handle:
            kernel32.CloseHandle(handle)


def main() -> int:
    set_dpi_awareness()

    if "--watchdog" in sys.argv[1:]:
        return run_watchdog(sys.argv[1:])

    restore_only = "--restore" in sys.argv[1:]
    if not is_admin():
        if not relaunch_as_admin(["--restore"] if restore_only else None):
            return 1
        return 0

    blocker = HostBlocker()
    if restore_only:
        blocker.restore()
        show_info("\u5df2\u6062\u590d\u77e5\u4e4e\u3001\u54d4\u54e9\u54d4\u54e9\u8bbf\u95ee\u3002")
        return 0

    instance = SingleInstance()
    if not instance.acquire():
        show_info("FocusTool \u5df2\u7ecf\u5728\u8fd0\u884c\u3002")
        return 0

    seconds = ask_duration()
    if seconds is None:
        return 0

    cleanup_done = False

    def cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        blocker.restore()
        cleanup_done = True

    def handle_signal(_signum, _frame) -> None:
        cleanup()
        raise SystemExit(0)

    atexit.register(cleanup)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except Exception:
            pass

    try:
        blocker.apply()
        start_restore_watchdog(os.getpid(), time.time() + seconds + 3)
    except Exception as exc:
        show_error(f"\u65e0\u6cd5\u5199\u5165 hosts \u6587\u4ef6\uff0c\u672a\u5f00\u59cb\u4e13\u6ce8\u3002\n\n{exc}")
        return 1

    try:
        overlay = CountdownOverlay(seconds, cleanup)
        overlay.run()
    finally:
        cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
