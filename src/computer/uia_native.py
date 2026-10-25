"""Mensagens Win32 limitadas a controles conhecidos da janela concedida."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
    wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM


def selected_handle(control, lease, allowed):
    hwnd = int(getattr(control, "handle", 0) or 0)
    if not hwnd or (hwnd != lease.hwnd and not user32.IsChild(lease.hwnd, hwnd)):
        raise ValueError("UIA_TARGET_INVALID: controle fora da janela atribuída")
    name = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, name, len(name))
    if name.value.lower() not in allowed:
        raise ValueError("UIA_PATTERN_UNSUPPORTED: padrão ausente neste controle")
    return hwnd


def send(hwnd, message, wparam=0, lparam=0):
    result = ctypes.c_size_t()
    if not user32.SendMessageTimeoutW(hwnd, message, wparam, lparam, 0x0002, 1500, ctypes.byref(result)):
        raise RuntimeError("UIA_MESSAGE_FAILED: controle indisponível ou tempo esgotado")
    return result.value


def invoke_button(control, lease):
    hwnd = selected_handle(control, lease, {"button"})
    send(hwnd, 0x00F5)  # BM_CLICK retorna zero normalmente; a entrega é verificada acima.


def set_text(control, lease, value):
    hwnd = selected_handle(control, lease, {"edit", "richedit20a", "richedit20w", "richedit50w"})
    text = ctypes.create_unicode_buffer(value)
    if not send(hwnd, 0x000C, lparam=ctypes.addressof(text)):
        raise RuntimeError("UIA_SET_VALUE_FAILED: WM_SETTEXT recusado")
    readback = ctypes.create_unicode_buffer(len(value) + 2)
    send(hwnd, 0x000D, len(readback), ctypes.addressof(readback))
    if readback.value != value:
        raise RuntimeError("UIA_SET_VALUE_FAILED: confirmação de texto falhou")
