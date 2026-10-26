"""Teste Empírico Adversarial de Isolamento de Sessão e Cursores no M4."""
from __future__ import annotations

import importlib
import threading
from typing import Generator
from unittest.mock import patch
import pytest

from src.computer import (
    get_agent_cursor_position,
    get_cursor_position,
    post_mouse_move,
    reset_agent_cursors,
    safety_gate,
)
from src.computer import mouse_background
from src.computer.window_assignments import window_assignments

assignments_module = importlib.import_module("src.computer.window_assignments")


@pytest.fixture(autouse=True)
def clean_cursors() -> Generator[None, None, None]:
    """Assegura isolamento limpo de cursores entre execuções de teste."""
    reset_agent_cursors()
    window_assignments.clear()
    yield
    reset_agent_cursors()
    window_assignments.clear()


@pytest.fixture
def assigned_windows(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Usa HWNDs sintéticos e PostMessageW simulado, sem entrada física."""
    monkeypatch.setattr(assignments_module.user32, "IsWindow", lambda _hwnd: 1)
    monkeypatch.setattr(assignments_module, "window_identity", lambda hwnd: (int(hwnd), 1))
    monkeypatch.setattr(mouse_background, "window_identity", lambda hwnd: (int(hwnd), 1))
    monkeypatch.setattr(
        mouse_background,
        "resolve_target_window",
        lambda x, y, hwnd=None: (int(hwnd), int(x), int(y)),
    )
    monkeypatch.setattr(mouse_background.user32, "PostMessageW", lambda *_args: 1)
    yield
    window_assignments.clear()


def test_edge_case_session_identifiers_and_isolation(
    reset_safety_gate: None, assigned_windows: None
) -> None:
    """Verifica comportamento adversarial com session_ids nulos, vazios e especiais."""
    safety_gate.authorize()
    try:
        window_assignments.assign("default", 3000)
        post_mouse_move(11, 22, hwnd=3000, session_id=None)
        assert get_agent_cursor_position("default") == (11, 22)
        assert get_agent_cursor_position(None) == (11, 22)

        post_mouse_move(33, 44, hwnd=3000, session_id="")
        assert get_agent_cursor_position("default") == (33, 44)

        post_mouse_move(55, 66, hwnd=3000, session_id="   ")
        assert get_agent_cursor_position("default") == (55, 66)

        window_assignments.assign("agente_especial_🌟", 3001)
        post_mouse_move(77, 88, hwnd=3001, session_id="agente_especial_🌟")
        assert get_agent_cursor_position("agente_especial_🌟") == (77, 88)
        assert get_agent_cursor_position("default") == (55, 66)
    finally:
        safety_gate.revoke("Fim do teste de session_id edge cases")


def test_stress_physical_cursor_remains_untouched(
    reset_safety_gate: None, assigned_windows: None
) -> None:
    """Garante que nenhum dos comandos concorrentes move o cursor físico do Windows."""
    safety_gate.authorize()
    try:
        cur_initial, num_agents = get_cursor_position(), 10
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [
                threading.Thread(
                    target=lambda i: [
                        post_mouse_move(i * 15, i * 25, hwnd=4000 + i, session_id=f"phy_test_{i}")
                        for _ in range(5)
                    ],
                    args=(i,),
                )
                for i in range(num_agents)
            ]
            for i in range(num_agents):
                window_assignments.assign(f"phy_test_{i}", 4000 + i)
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)
        cur_final = get_cursor_position()
        assert (
            abs(cur_final[0] - cur_initial[0]) <= 5 and abs(cur_final[1] - cur_initial[1]) <= 5
        ), f"Cursor físico do usuário foi movido além do jitter aceitável: {cur_final} != {cur_initial}"
    finally:
        safety_gate.revoke("Fim do teste de não invasão física")
