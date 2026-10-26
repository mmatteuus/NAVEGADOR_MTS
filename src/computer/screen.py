"""Módulo de Captura de Tela Multi-Monitor com Suporte Universal a High-DPI no Windows.

Permite captura em alta resolução da área de trabalho virtual completa
(SM_XVIRTUALSCREEN), de monitores específicos ou de regiões retangulares,
utilizando GDI nativo de alto desempenho e serialização Base64.
"""

import base64
import ctypes
from ctypes import wintypes
import io
from typing import Dict, Any, Optional, List
from PIL import Image
from .win32_types import (
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
)
from .safety_gate import safety_gate

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def _enable_high_dpi_awareness() -> None:
    """Ativa Per-Monitor DPI Awareness com fallback para Windows 10, 11 e Server."""
    try:
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_high_dpi_awareness()


class BITMAPINFOHEADER(ctypes.Structure):
    """Cabeçalho de informações de bitmap para extração direta via GetDIBits."""
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def get_monitors_info() -> List[Dict[str, Any]]:
    """Enumera todos os monitores conectados e suas respectivas geometrias."""
    monitors: List[Dict[str, Any]] = []

    def _monitor_enum_proc(hmon, hdc, lprect, lparam):
        r = lprect.contents
        monitors.append({
            "index": len(monitors), "x": int(r.left), "y": int(r.top),
            "width": int(r.right - r.left), "height": int(r.bottom - r.top),
        })
        return 1

    cb = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)(_monitor_enum_proc)
    user32.EnumDisplayMonitors(0, 0, cb, 0)
    return monitors


def _capture_raw_gdi(x: int, y: int, w: int, h: int) -> Image.Image:
    """Captura uma área retangular da tela via BitBlt e retorna objeto PIL.Image."""
    hdesk = user32.GetDesktopWindow()
    hdc_screen = user32.GetDC(hdesk)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

    try:
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020 | 0x40000000)
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount, bmi.biCompression = w, -h, 1, 32, 0
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
        return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    finally:
        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hdesk, hdc_screen)


def capture_screen(
    monitor_index: Optional[int] = None,
    region: Optional[Dict[str, int]] = None,
    format: str = "png"
) -> Dict[str, Any]:
    """Captura a tela inteira, um monitor ou uma região, retornando base64."""
    safety_gate.check_authorization("capture_screen")
    monitors = get_monitors_info()

    if region:
        img = _capture_raw_gdi(int(region["x"]), int(region["y"]), int(region["width"]), int(region["height"]))
    elif monitor_index is not None and 0 <= monitor_index < len(monitors):
        m = monitors[monitor_index]
        img = _capture_raw_gdi(m["x"], m["y"], m["width"], m["height"])
    else:
        vx, vy = user32.GetSystemMetrics(SM_XVIRTUALSCREEN), user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw, vh = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN), user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        img = _capture_raw_gdi(vx, vy, vw, vh)

    ext = "JPEG" if format.lower() in ("jpg", "jpeg") else "PNG"
    stream = io.BytesIO()
    img.save(stream, format=ext, quality=85 if ext == "JPEG" else None)
    b64_data = base64.b64encode(stream.getvalue()).decode("utf-8")

    try: dpi = int(user32.GetDpiForSystem()) or 96
    except Exception: dpi = 96

    return {
        "imageBase64": b64_data, "width": img.width, "height": img.height,
        "dpiScale": round(dpi / 96.0, 2), "format": ext.lower(),
    }
