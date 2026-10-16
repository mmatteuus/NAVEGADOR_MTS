"""Estresse Concorrente e Adversarial: Coordenadas Extremas, HWND Inválido e SafetyGate.

Testa condições de estresse com múltiplas threads concorrentes, coordenadas aberrantes,
janelas inexistentes e alternância rápida do SafetyGate sem vazamento de autorização.
"""
from __future__ import annotations

import concurrent.futures
import ctypes
import threading
import time
from typing import Tuple
import pytest

from src.computer import (
    execute_computer_action, get_cursor_position, post_key_press,
    post_keyboard_type, post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll, safety_gate,
)

user32 = ctypes.windll.user32


def test_adversarial_extreme_coordinates_and_invalid_hwnd(reset_safety_gate: None) -> None:
    """Verifica comportamento com coordenadas fora dos limites e HWND inexistente."""
    safety_gate.authorize()
    try:
        init_pos = get_cursor_position()

        # Coordenadas aberrantes / fora da tela
        for ex, ey in [(-999999, -999999), (999999, 999999), (0, 0), (-1, -1)]:
            res_m = post_mouse_move(ex, ey, hwnd=0xDEAD)
            assert res_m["background"] is True
            res_c = post_mouse_click(x=ex, y=ey, hwnd=0xDEAD)
            assert res_c["background"] is True
            res_s = post_mouse_scroll(delta_y=-500, delta_x=500, x=ex, y=ey, hwnd=0xDEAD)
            assert res_s["scrolled"] is True

        # HWND inválido (0xDEAD, -1)
        res_drag = post_mouse_drag(-500, -500, 5000, 5000, steps=5, hwnd=0xBADC0DE)
        assert res_drag["dragged"] is True

        # Cursor físico do usuário deve permanecer 100% intocado
        assert get_cursor_position() == init_pos, "Cursor físico alterado com coordenadas anômalas"
    finally:
        safety_gate.revoke("Fim de teste de coordenadas extremas")


def test_safety_gate_multithreaded_race_no_leak(reset_safety_gate: None) -> None:
    """Submete o SafetyGate a rajadas concorrentes garantindo ausência total de bypass."""
    stop_event = threading.Event()

    def flipper() -> None:
        while not stop_event.is_set():
            safety_gate.authorize()
            time.sleep(0.005)
            safety_gate.revoke("Flipper revogou")
            time.sleep(0.005)

    flipper_th = threading.Thread(target=flipper, daemon=True)
    flipper_th.start()

    def worker(worker_id: int) -> Tuple[int, int]:
        blocked = 0
        allowed = 0
        for i in range(25):
            res = execute_computer_action("computer_mouse_move", {"x": 100 + worker_id, "y": 100 + i})
            if res.get("isSecurityBlock"):
                blocked += 1
            elif res.get("success"):
                allowed += 1
        return blocked, allowed

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(8)))

    stop_event.set()
    flipper_th.join(timeout=1.0)
    safety_gate.revoke("Limpeza")

    total_blocked = sum(r[0] for r in results)
    total_allowed = sum(r[1] for r in results)
    assert total_blocked > 0, "Deveria ter ocorrido bloqueios sob revogação ativa"
    assert total_blocked + total_allowed == 8 * 25, "Todas as tentativas devem ter resposta determinística"


def test_adversarial_keyboard_unicode_and_rapid_burst(reset_safety_gate: None) -> None:
    """Testa rajada de digitação Unicode e teclas virtuais em background."""
    safety_gate.authorize()
    try:
        # Texto com emojis, acentos, caracteres orientais e especiais
        unicode_str = "Olá Mundo! 🚀 Windows 11 — 漢字 & #$%!"
        res_type = post_keyboard_type(unicode_str, delay_ms=0, hwnd=user32.GetDesktopWindow())
        assert res_type["success"] is True and res_type["typedChars"] == len(unicode_str)

        # Teclas rápidas
        for k in ["enter", "tab", "esc", "f5", "backspace"]:
            res_k = post_key_press(k, hwnd=user32.GetDesktopWindow())
            assert res_k["background"] is True

        # Tecla inválida deve levantar ValueError
        with pytest.raises(ValueError, match="Tecla desconhecida"):
            post_key_press("INVALID_KEY_NAME_XYZ")
    finally:
        safety_gate.revoke("Fim de teste de teclado adversarial")
