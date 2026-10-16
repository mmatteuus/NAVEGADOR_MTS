"""Módulo de Controle Virtual de Teclado em Segundo Plano (Background Win32).

Despacha teclas e caracteres Unicode via PostMessageW diretamente para a janela alvo,
sem roubar o foco ativo da janela em que o usuário está trabalhando.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import time
from typing import Any, Dict, List, Optional
from .safety_gate import safety_gate
from .window_finder import find_window_at
from .mouse_background import get_agent_cursor_position

user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

VK_MAP = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "escape": 0x1B, "esc": 0x1B,
    "shift": 0x10, "control": 0x11, "ctrl": 0x11, "alt": 0x12,
    "win": 0x5B, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
    **{chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)},
    **{str(n): 0x30 + n for n in range(10)}
}


def _resolve_target_hwnd(hwnd: Optional[int] = None) -> int:
    """Resolve a janela alvo a partir do hwnd fornecido ou da posição virtual do agente."""
    if hwnd and user32.IsWindow(wintypes.HWND(hwnd)):
        return int(hwnd)
    ax, ay = get_agent_cursor_position()
    return find_window_at(ax, ay)


def post_keyboard_type(
    text: str, delay_ms: int = 5, hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """Digita texto Unicode enviando mensagens WM_CHAR para a janela em background."""
    safety_gate.check_authorization("type_text")
    target_hwnd = _resolve_target_hwnd(hwnd)
    hw = wintypes.HWND(target_hwnd)
    delay_sec = max(delay_ms / 1000.0, 0.001)

    for char in text:
        user32.PostMessageW(hw, WM_CHAR, ord(char), 1)
        if delay_ms > 0:
            time.sleep(delay_sec)

    return {
        "typedChars": len(text),
        "success": True,
        "background": True,
        "targetHwnd": target_hwnd
    }


def post_key_press(
    key: str, modifiers: Optional[List[str]] = None, hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """Pressiona teclas e combinações via WM_KEYDOWN/WM_KEYUP sem alterar foco."""
    safety_gate.check_authorization("press_key")
    target_hwnd = _resolve_target_hwnd(hwnd)
    hw = wintypes.HWND(target_hwnd)
    mod_vks = [VK_MAP[m.lower()] for m in (modifiers or []) if m.lower() in VK_MAP]

    target_vk = VK_MAP.get(key.lower())
    if not target_vk and len(key) == 1:
        target_vk = ord(key.upper())
    if not target_vk:
        raise ValueError(f"Tecla desconhecida: '{key}'")

    for m_vk in mod_vks:
        user32.PostMessageW(hw, WM_KEYDOWN, m_vk, 1)
        time.sleep(0.01)

    user32.PostMessageW(hw, WM_KEYDOWN, target_vk, 1)
    time.sleep(0.02)
    user32.PostMessageW(hw, WM_KEYUP, target_vk, 0xC0000001)

    for m_vk in reversed(mod_vks):
        user32.PostMessageW(hw, WM_KEYUP, m_vk, 0xC0000001)
        time.sleep(0.01)

    return {
        "executedKey": key,
        "modifiers": modifiers or [],
        "background": True,
        "targetHwnd": target_hwnd
    }
