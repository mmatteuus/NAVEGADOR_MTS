"""Teste Empírico Adversarial de Concorrência e Estresse Multithread no M4."""
from __future__ import annotations

import importlib
import threading
from typing import Generator
from unittest.mock import patch
import pytest

from src.computer import (
    execute_computer_action,
    get_agent_cursor_position,
    post_mouse_click,
    post_mouse_move,
    post_mouse_scroll,
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


def test_stress_12_agents_concurrent_virtual_cursors(
    reset_safety_gate: None, assigned_windows: None
) -> None:
    """Dispara 12 agentes simultâneos validando ausência de vazamento de coordenadas."""
    safety_gate.authorize()
    errors, num_agents, iterations = [], 12, 20

    def _agent_worker(agent_id: int) -> None:
        sid, hwnd = f"agent_stress_{agent_id}", 1000 + agent_id
        window_assignments.assign(sid, hwnd)
        for step in range(1, iterations + 1):
            expected_x = agent_id * 100 + step
            expected_y = agent_id * 200 + step
            try:
                post_mouse_move(expected_x, expected_y, hwnd=hwnd, session_id=sid)
                pos = get_agent_cursor_position(sid)
                if pos != (expected_x, expected_y):
                    errors.append(f"Agente {sid} passo {step}: esperado {(expected_x, expected_y)}, obteve {pos}")
                post_mouse_click(hwnd=hwnd, session_id=sid)
                res = execute_computer_action("computer_get_agent_cursor", {"session_id": sid})
                if not res.get("success") or res["data"]["x"] != expected_x or res["data"]["y"] != expected_y:
                    errors.append(f"Consulta MCP falhou para {sid}: {res}")
            except Exception as exc:
                errors.append(f"Exceção no agente {sid}: {exc}")

    try:
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [threading.Thread(target=_agent_worker, args=(i,)) for i in range(num_agents)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)
                if t.is_alive():
                    errors.append("Timeout / Deadlock detectado em thread de agente")

        assert not errors, f"Erros durante estresse multithread: {errors}"
        for i in range(num_agents):
            sid = f"agent_stress_{i}"
            expected = (i * 100 + iterations, i * 200 + iterations)
            assert get_agent_cursor_position(sid) == expected, f"Posição final divergente para {sid}"
    finally:
        safety_gate.revoke("Fim do estresse de 12 agentes")


def test_stress_cursor_lock_high_contention_no_deadlock(
    reset_safety_gate: None, assigned_windows: None
) -> None:
    """Submete _cursor_lock a contenção agressiva com 16 threads misturando ações."""
    safety_gate.authorize()
    errors, num_threads = [], 16

    def _contention_worker(idx: int) -> None:
        sid, hwnd = f"contention_agent_{idx}", 2000 + idx
        window_assignments.assign(sid, hwnd)
        try:
            for step in range(1, 15):
                post_mouse_move(idx * 10 + step, idx * 20 + step, hwnd=hwnd, session_id=sid)
                post_mouse_click(hwnd=hwnd, session_id=sid)
                post_mouse_scroll(delta_y=10, hwnd=hwnd, session_id=sid)
                get_agent_cursor_position(sid)
                get_agent_cursor_position(f"contention_agent_{(idx + 1) % num_threads}")
        except Exception as exc:
            errors.append(exc)

    try:
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [threading.Thread(target=_contention_worker, args=(i,)) for i in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=8.0)
                assert not t.is_alive(), "Deadlock detectado em _cursor_lock sob alta contenção"
        assert not errors, f"Exceções sob contenção: {errors}"
    finally:
        safety_gate.revoke("Fim do teste de contenção de lock")
