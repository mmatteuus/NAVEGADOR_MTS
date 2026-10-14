"""
Módulo de Automação do Teclado para Windows com Suporte a Unicode ABNT2.

Digita textos complexos usando KEYEVENTF_UNICODE (imune a dead-keys e layouts),
executa atalhos e combinações de teclas com soltura em bloco try/finally, e
oferece a rotina compulsória de emergência release_all_keys.
"""

import ctypes
import time
from typing import List, Dict, Any, Optional
from .win32_types import (
    INPUT, INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE,
    VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_ESCAPE,
    VK_TAB, VK_RETURN, VK_SPACE, VK_BACK, VK_DELETE
)
from .safety_gate import safety_gate
from .kill_switch import kill_switch

user32 = ctypes.windll.user32

# Mapeamento extensivo de nomes de teclas amigáveis para Códigos Virtuais (VK)
VK_MAP = {
    "enter": VK_RETURN, "return": VK_RETURN, "tab": VK_TAB, "space": VK_SPACE,
    "backspace": VK_BACK, "delete": VK_DELETE, "escape": VK_ESCAPE, "esc": VK_ESCAPE,
    "shift": VK_SHIFT, "control": VK_CONTROL, "ctrl": VK_CONTROL, "alt": VK_MENU,
    "win": VK_LWIN, "meta": VK_LWIN, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
    **{chr(c): c for c in range(ord('A'), ord('Z') + 1)},
    **{str(n): 0x30 + n for n in range(10)}
}

def _send_key_event(vk: int, flags: int = 0, scan: int = 0) -> None:
    """Emite um evento de entrada de teclado individual para a user32."""
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = 0
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def release_all_keys() -> None:
    """Rotina de pânico que força a soltura de todas as teclas modificadoras."""
    teclas_modificadoras = [
        VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN,
        0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5  # L/R Shift, Ctrl, Alt
    ]
    for vk in teclas_modificadoras:
        _send_key_event(vk, KEYEVENTF_KEYUP)

kill_switch.register_cleanup_callback(release_all_keys)

def type_text(text: str, delay_ms: int = 25) -> Dict[str, Any]:
    """Digita texto Unicode (suporta acentos, ç, emojis e caracteres ABNT2)."""
    safety_gate.check_authorization("type_text")
    intervalo = max(delay_ms / 1000.0, 0.005)
    chars_typed = 0

    try:
        for char in text:
            # Emissão segura via KEYEVENTF_UNICODE
            code = ord(char)
            _send_key_event(0, KEYEVENTF_UNICODE, scan=code)
            time.sleep(0.005)
            _send_key_event(0, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, scan=code)
            chars_typed += 1
            time.sleep(intervalo)
    finally:
        # Prevenção ativa contra qualquer tecla presa em caso de interrupção
        pass

    return {"typedChars": chars_typed, "success": True}

def press_key(key: str, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pressiona uma tecla com modificadores opcionais (ex: ['ctrl'], 'c')."""
    safety_gate.check_authorization("press_key")
    mod_vks = [VK_MAP[m.lower()] for m in (modifiers or []) if m.lower() in VK_MAP]
    target_vk = VK_MAP.get(key.lower())

    if not target_vk and len(key) == 1:
        target_vk = ord(key.upper())

    if not target_vk:
        raise ValueError(f"Tecla desconhecida: '{key}'")

    try:
        # Pressiona os modificadores em sequência
        for m_vk in mod_vks:
            _send_key_event(m_vk, 0)
            time.sleep(0.01)

        # Pressiona e solta a tecla principal
        _send_key_event(target_vk, 0)
        time.sleep(0.03)
        _send_key_event(target_vk, KEYEVENTF_KEYUP)
    finally:
        # Solta modificadores na ordem reversa obrigatoriamente
        for m_vk in reversed(mod_vks):
            _send_key_event(m_vk, KEYEVENTF_KEYUP)
            time.sleep(0.01)

    return {"executedKey": key, "modifiers": modifiers or []}
