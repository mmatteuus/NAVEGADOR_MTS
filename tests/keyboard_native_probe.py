"""Probe opt-in de teclado background em controles EDIT nativos próprios."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.computer import post_keyboard_type, safety_gate

user32 = ctypes.windll.user32
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
ES_MULTILINE = 0x0004
PM_REMOVE = 0x0001


def _text(hwnd: int) -> str:
    size = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(size + 1)
    user32.GetWindowTextW(hwnd, buf, size + 1)
    return buf.value


def _pump(seconds: float = 0.2) -> None:
    deadline = time.monotonic() + seconds
    msg = wintypes.MSG()
    while time.monotonic() < deadline:
        while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.005)


def main() -> int:
    controls = []
    try:
        for _ in range(2):
            hwnd = user32.CreateWindowExW(
                0, "EDIT", "", WS_POPUP | WS_VISIBLE | ES_MULTILINE,
                -10000, -10000, 300, 80, 0, 0, 0, None
            )
            if not hwnd:
                raise RuntimeError("CreateWindowExW falhou")
            controls.append(hwnd)
        foreground_before = int(user32.GetForegroundWindow() or 0)
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        cursor_before = (point.x, point.y)
        safety_gate.authorize()
        result = post_keyboard_type("Agente 😀 isolado", delay_ms=0, hwnd=int(controls[0]))
        _pump()
        safety_gate.revoke("Fim do probe nativo")
        user32.GetCursorPos(ctypes.byref(point))
        assert result["success"] and result["typedChars"] == len("Agente 😀 isolado")
        assert _text(controls[0]) == "Agente 😀 isolado"
        assert _text(controls[1]) == ""
        assert int(user32.GetForegroundWindow() or 0) == foreground_before
        assert (point.x, point.y) == cursor_before
        print("PASS keyboard_native_probe: texto, foco, cursor e controle não alvo preservados")
        return 0
    finally:
        safety_gate.revoke("Limpeza do probe nativo")
        for hwnd in controls:
            user32.DestroyWindow(hwnd)


if __name__ == "__main__":
    raise SystemExit(main())
