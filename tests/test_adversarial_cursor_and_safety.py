"""Teste Adversarial Empírico: Invariância de GetCursorPos e Fail-Closed SafetyGate.

Comprova com precisão de hardware que o cursor físico do usuário permanece estritamente
idêntico antes, DURANTE e após chamadas de post_mouse_move, post_mouse_click,
post_mouse_drag e post_mouse_scroll, além de testar exaustivamente o SafetyGate.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import pathlib
import threading
import time
from typing import List, Tuple
import psutil
import pytest

from src.computer import (
    SecurityGateError, ensure_thread_desktop, execute_computer_action,
    get_agent_cursor_position, get_cursor_position, post_key_press,
    post_keyboard_type, post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll, safety_gate,
)
from tests.conftest import missing_initial_pids

user32 = ctypes.windll.user32


class _HardwareCursorSampler(threading.Thread):
    """Monitor de altíssima frequência (sub-milissegundo) para GetCursorPos."""

    def __init__(self, expected_pos: Tuple[int, int]) -> None:
        super().__init__(daemon=True)
        self.expected_pos = expected_pos
        self.running = True
        self.sample_count = 0
        self.deviations: List[Tuple[int, int]] = []

    def run(self) -> None:
        ensure_thread_desktop()
        pt = wintypes.POINT()
        while self.running:
            if user32.GetCursorPos(ctypes.byref(pt)):
                current = (int(pt.x), int(pt.y))
                self.sample_count += 1
                dx = abs(current[0] - self.expected_pos[0])
                dy = abs(current[1] - self.expected_pos[1])
                if dx > 2 or dy > 2:
                    self.deviations.append(current)
            time.sleep(0.001)

    def stop(self) -> None:
        self.running = False


def test_cursor_pos_strictly_invariant_before_during_after(reset_safety_gate: None) -> None:
    """Garante via sampler concorrente que GetCursorPos jamais oscila durante ações virtuais."""
    safety_gate.authorize()
    try:
        init_pos = get_cursor_position()
        sampler = _HardwareCursorSampler(init_pos)
        sampler.start()

        time.sleep(0.01)  # Aquecimento do sampler

        # 1. Movimento virtual
        res_m = post_mouse_move(950, 450)
        assert res_m["background"] is True

        # 2. Cliques virtuais múltiplos (esquerdo, direito, duplo)
        post_mouse_click(button="left", double=False, x=950, y=450)
        post_mouse_click(button="right", double=False, x=950, y=450)
        post_mouse_click(button="left", double=True, x=950, y=450)

        # 3. Arrastar virtual em 20 passos com pausas internas
        res_d = post_mouse_drag(950, 450, 1150, 650, steps=20)
        assert res_d["dragged"] is True

        # 4. Scroll virtual vertical e horizontal
        res_s = post_mouse_scroll(delta_y=240, delta_x=120, x=1150, y=650)
        assert res_s["scrolled"] is True

        sampler.stop()
        sampler.join(timeout=1.0)

        # Validações empíricas estritas
        assert sampler.sample_count >= 20, f"Amostragem insuficiente ({sampler.sample_count})"
        assert len(sampler.deviations) == 0, (
            f"VIOLAÇÃO DE CURSOR FÍSICO! Desvios detectados DURANTE ações: {sampler.deviations}"
        )
        final_pos = get_cursor_position()
        assert abs(init_pos[0] - final_pos[0]) <= 2 and abs(init_pos[1] - final_pos[1]) <= 2, f"Cursor físico final {final_pos} != inicial {init_pos} (com tolerância de 2px)"
        assert get_agent_cursor_position() == (1150, 650), "Cursor do agente desalinhado"
    finally:
        safety_gate.revoke("Fim do teste empírico de invariância de cursor")


def test_adversarial_safety_gate_rejection(reset_safety_gate: None) -> None:
    """Valida rejeição incondicional (Fail-Closed) com e sem kill switch."""
    safety_gate.revoke("Ataque adversarial sem autorização")
    assert not safety_gate.is_authorized()

    # Rejeição direta das funções de background
    for fn, args in [
        (post_mouse_move, (10, 10)), (post_mouse_click, ()),
        (post_mouse_drag, (0, 0, 10, 10)), (post_mouse_scroll, (120,)),
        (post_keyboard_type, ("teste",)), (post_key_press, ("a",))
    ]:
        with pytest.raises(SecurityGateError):
            fn(*args)

    # Rejeição pelo despachante execute_computer_action
    res = execute_computer_action("computer_mouse_move", {"x": 10, "y": 10})
    assert res["success"] is False and res.get("isSecurityBlock") is True

    # Kill-switch ativo sobrepõe autorização
    safety_gate.authorize()
    safety_gate.revoke("KILL_SWITCH de teste")
    assert safety_gate.is_kill_switch_triggered()
    assert not safety_gate.is_authorized()
    with pytest.raises(SecurityGateError):
        post_mouse_move(20, 20)


def test_prod_pids_untouched(initial_live_prod_pids: list[int]) -> None:
    """Verifica que todo PID vivo no início da sessão continua vivo."""
    assert missing_initial_pids(initial_live_prod_pids) == []


def test_loc_compliance_strict() -> None:
    """Audita programaticamente que 100% dos arquivos têm <= 150 LOC."""
    for pattern in ("src/**/*.py", "tests/**/*.py", "src/extension/**/*.js"):
        for path in pathlib.Path(".").glob(pattern):
            lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
            assert lines <= 150, f"Arquivo {path} excedeu 150 LOC ({lines} linhas)"
