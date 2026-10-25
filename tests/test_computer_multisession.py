"""Suíte de Testes para Concorrência e Isolamento Multissessão no Computer Use.

Valida o particionamento de cursor virtual por agente em mouse_background.py,
o mutex _physical_device_lock em mouse.py, o despacho multissessão e Fail-Closed.
"""
from __future__ import annotations
import threading
import time
from unittest.mock import patch
from typing import Generator
import pytest
from src.computer import (
    SecurityGateError, _physical_device_lock, execute_computer_action,
    get_agent_cursor_position, post_mouse_click, post_mouse_move,
    reset_agent_cursors, safety_gate,
)


@pytest.fixture(autouse=True)
def clean_agent_cursors(monkeypatch) -> Generator[None, None, None]:
    """Garante ambiente limpo para cursores de agentes antes e pós teste."""
    monkeypatch.setattr("src.computer.mouse_background._lease", lambda *a, **k: None)
    reset_agent_cursors()
    yield
    reset_agent_cursors()


def test_virtual_cursor_isolation_between_sessions(reset_safety_gate: None) -> None:
    """Verifica isolamento estrito de coordenadas virtuais entre múltiplos agentes."""
    safety_gate.authorize()
    try:
        post_mouse_move(100, 200, session_id="agent_alpha")
        post_mouse_move(500, 600, session_id="agent_beta")

        assert get_agent_cursor_position("agent_alpha") == (100, 200)
        assert get_agent_cursor_position("agent_beta") == (500, 600)
        assert get_agent_cursor_position("agent_gamma") == (0, 0)
        assert get_agent_cursor_position(None) == (0, 0)

        post_mouse_click(session_id="agent_alpha")
        assert get_agent_cursor_position("agent_alpha") == (100, 200)
        assert get_agent_cursor_position("agent_beta") == (500, 600)

        res_a = execute_computer_action("computer_get_agent_cursor", {"session_id": "agent_alpha"})
        res_b = execute_computer_action("computer_get_agent_cursor", {"sessionId": "agent_beta"})
        assert res_a["success"] and res_a["data"]["x"] == 100 and res_a["data"]["x"] == 100
        assert res_b["success"] and res_b["data"]["x"] == 500 and res_b["data"]["y"] == 600
    finally:
        safety_gate.revoke("Fim do teste de isolamento multissessão")


def test_concurrent_multithreaded_virtual_cursors(reset_safety_gate: None) -> None:
    """Valida execução concorrente de múltiplos agentes sem contaminação mútua."""
    safety_gate.authorize()
    errors: list[Exception] = []
    num_agents = 6

    def _worker(idx: int) -> None:
        sid = f"agent_worker_{idx}"
        try:
            for step in range(1, 6):
                post_mouse_move(idx * 50 + step * 2, idx * 30 + step * 2, session_id=sid)
                post_mouse_click(session_id=sid)
        except Exception as exc:
            errors.append(exc)

    try:
        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(num_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)

        assert not errors, f"Erros durante execução multithread: {errors}"
        for i in range(num_agents):
            expected = (i * 50 + 10, i * 30 + 10)
            assert get_agent_cursor_position(f"agent_worker_{i}") == expected
    finally:
        safety_gate.revoke("Fim do teste de estresse concorrente")


def test_physical_device_lock_serializes_hardware_access(reset_safety_gate: None) -> None:
    """Verifica que o mutex _physical_device_lock serializa operações físicas de hardware."""
    safety_gate.authorize()
    lock_observed: list[bool] = []

    def mock_set_cursor(x: int, y: int) -> None:
        lock_observed.append(_physical_device_lock.locked())
        time.sleep(0.01)

    try:
        with patch("src.computer.mouse.user32.SetCursorPos", side_effect=mock_set_cursor):
            res = execute_computer_action(
                "computer_mouse_move", {"x": 50, "y": 50, "background": False, "smooth": False}
            )
            assert res["success"] is True
            assert any(lock_observed), "O mutex _physical_device_lock deve estar travado durante SetCursorPos"
            assert not _physical_device_lock.locked(), "O mutex deve ser liberado após o comando"
    finally:
        safety_gate.revoke("Fim do teste de lock físico")


def test_multisession_fail_closed_security_gate(reset_safety_gate: None) -> None:
    """Valida que o SafetyGate permanece Fail-Closed em todas as sessões."""
    assert not safety_gate.is_authorized()

    res_a = execute_computer_action("computer_mouse_move", {"x": 100, "y": 100, "session_id": "agent_x"})
    assert res_a["success"] is False and res_a.get("isSecurityBlock") is True

    res_b = execute_computer_action("computer_mouse_click", {"sessionId": "agent_y"})
    assert res_b["success"] is False and res_b.get("isSecurityBlock") is True

    with pytest.raises(SecurityGateError):
        post_mouse_move(200, 200, session_id="agent_unauthorized")

    with pytest.raises(SecurityGateError):
        post_mouse_click(session_id="agent_unauthorized")
