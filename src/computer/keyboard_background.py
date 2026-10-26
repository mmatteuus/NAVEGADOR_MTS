"""Módulo de Controle Virtual de Teclado em Segundo Plano (Background Win32).

Despacha teclas e caracteres Unicode via PostMessageW diretamente para a janela alvo,
sem roubar o foco ativo da janela em que o usuário está trabalhando.
"""

from __future__ import annotations

import ctypes, functools, threading, time
from ctypes import wintypes
from typing import Any, Dict, List, Optional
from .safety_gate import safety_gate
from .keyboard_target import keyboard_target_identity, resolve_keyboard_target, revalidate_keyboard_target
from .window_assignments import window_assignments

_lock_guard = threading.Lock()
_keyboard_locks: Dict[str, threading.RLock] = {}


def _serialized(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        key = str(kwargs.get("session_id") or kwargs.get("hwnd") or "default")
        with _lock_guard:
            lock = _keyboard_locks.setdefault(key, threading.RLock())
        with lock:
            return function(*args, **kwargs)
    return wrapper


def _resolve(hwnd: Optional[int], session_id: Optional[str]) -> int:
    return resolve_keyboard_target(hwnd, session_id=session_id) if session_id else resolve_keyboard_target(hwnd)


user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
VK_MAP = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "space": 0x20, "backspace": 0x08, "delete": 0x2E,
    "escape": 0x1B, "esc": 0x1B, "shift": 0x10, "control": 0x11, "ctrl": 0x11, "alt": 0x12,
    "win": 0x5B, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
    **{chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)},
    **{str(n): 0x30 + n for n in range(10)}
}


@_serialized
def post_keyboard_type(
    text: str, delay_ms: int = 5, hwnd: Optional[int] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    safety_gate.check_authorization("type_text")
    target_hwnd = _resolve(hwnd, session_id)
    target_identity = keyboard_target_identity(target_hwnd)
    lease = window_assignments.get(session_id) if session_id else None
    if session_id:
        if lease is None or lease.hwnd != target_hwnd:
            raise ValueError("TARGET_REVOKED: atribuição ausente durante a operação")
        if not getattr(lease, "allow_keyboard", True):
            raise ValueError("DEVICE_DISABLED: controle de teclado desativado pelo usuário para esta janela")
    hw = wintypes.HWND(target_hwnd)
    delay_sec = max(delay_ms / 1000.0, 0.001)

    for char in text:
        safety_gate.check_authorization("type_text")
        if session_id:
            revalidate_keyboard_target(target_hwnd, target_identity, session_id=session_id, lease=lease)
        else:
            revalidate_keyboard_target(target_hwnd, target_identity)
        units = char.encode("utf-16-le", errors="surrogatepass")
        for index in range(0, len(units), 2):
            unit = int.from_bytes(units[index:index + 2], "little")
            if not user32.PostMessageW(hw, WM_CHAR, unit, 1):
                raise RuntimeError("KEYBOARD_POST_FAILED: WM_CHAR não entrou na fila")
        if delay_ms > 0:
            time.sleep(delay_sec)

    return {"typedChars": len(text), "success": True, "background": True, "targetHwnd": target_hwnd}


@_serialized
def post_key_press(
    key: str, modifiers: Optional[List[str]] = None, hwnd: Optional[int] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    safety_gate.check_authorization("press_key")
    mod_vks, allowed_modifiers = [], {"shift", "control", "ctrl", "alt", "win", "meta"}
    for modifier in modifiers or []:
        if modifier.lower() not in allowed_modifiers:
            raise ValueError(f"Tecla desconhecida: '{modifier}'")
        mod_vks.append(VK_MAP["win"] if modifier.lower() == "meta" else VK_MAP[modifier.lower()])

    target_vk = VK_MAP.get(key.lower()) or (ord(key.upper()) if len(key) == 1 and key.isascii() else None)
    if not target_vk:
        raise ValueError(f"Tecla desconhecida: '{key}'")

    target_hwnd = _resolve(hwnd, session_id)
    target_identity = keyboard_target_identity(target_hwnd)
    lease = window_assignments.get(session_id) if session_id else None
    if session_id:
        if lease is None or lease.hwnd != target_hwnd:
            raise ValueError("TARGET_REVOKED: atribuição ausente durante a operação")
        if not getattr(lease, "allow_keyboard", True):
            raise ValueError("DEVICE_DISABLED: controle de teclado desativado pelo usuário para esta janela")
    hw = wintypes.HWND(target_hwnd)

    pressed, release_failures, completed = [], [], False
    try:
        for m_vk in mod_vks + [target_vk]:
            safety_gate.check_authorization("press_key")
            if session_id:
                revalidate_keyboard_target(target_hwnd, target_identity, session_id=session_id, lease=lease)
            else:
                revalidate_keyboard_target(target_hwnd, target_identity)
            if not user32.PostMessageW(hw, WM_KEYDOWN, m_vk, 1):
                raise RuntimeError("KEYBOARD_POST_FAILED: WM_KEYDOWN não entrou na fila")
            pressed.append(m_vk)
            time.sleep(0.01)
        time.sleep(0.01)
        completed = True
    finally:
        for vk in reversed(pressed):
            if keyboard_target_identity(target_hwnd) != target_identity:
                release_failures.append(vk)
                continue
            if not user32.PostMessageW(hw, WM_KEYUP, vk, 0xC0000001):
                release_failures.append(vk)
    if completed and release_failures:
        raise RuntimeError("KEYBOARD_RELEASE_FAILED: não foi possível liberar todas as teclas")

    return {"executedKey": key, "modifiers": modifiers or [], "background": True, "targetHwnd": target_hwnd}
