"""Teste Empírico Adversarial de Concorrência e Estresse Multithread no M4.

Valida isolamento de 10+ agentes simultâneos em mouse_background.py, ausência
de deadlocks em _cursor_lock sob alta contenção e integridade de coordenadas.
"""
from __future__ import annotations
import threading
import importlib
from typing import Generator
from unittest.mock import patch
import pytest
from src.computer import (
    execute_computer_action, get_agent_cursor_position,
    get_cursor_position, post_mouse_click,
    post_mouse_move, post_mouse_scroll, reset_agent_cursors, safety_gate,
)
from src.computer import mouse_background
from src.computer.window_assignments import window_assignments
assignments_module = importlib.import_module("src.computer.window_assignments")


@pytest.fixture(autouse=True)
def clean_cursors() -> Generator[None, None, None]:
    """Assegura isolamento limpo de cursores entre execuções de teste."""
    reset_agent_cursors()
    yield
    reset_agent_cursors()


@pytest.fixture
def assigned_windows(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Usa HWNDs sintéticos e PostMessageW simulado, sem entrada física."""
    monkeypatch.setattr(assignments_module.user32, "IsWindow", lambda _hwnd: 1)
    monkeypatch.setattr(assignments_module, "window_identity", lambda hwnd: (int(hwnd), 1))
    monkeypatch.setattr(mouse_background, "window_identity", lambda hwnd: (int(hwnd), 1))
    monkeypatch.setattr(mouse_background, "resolve_target_window", lambda x, y, hwnd=None: (int(hwnd), int(x), int(y)))
    monkeypatch.setattr(mouse_background.user32, "PostMessageW", lambda *_args: 1)
    yield
    window_assignments.clear()


def test_stress_12_agents_concurrent_virtual_cursors(reset_safety_gate: None, assigned_windows: None) -> None:
    """Dispara 12 agentes simultâneos validando ausência de vazamento de coordenadas."""
    safety_gate.authorize()
    errors, num_agents, iterations = [], 12, 20

    def _agent_worker(agent_id: int) -> None:
        sid, hwnd = f"agent_stress_{agent_id}", 1000 + agent_id
        window_assignments.assign(sid, hwnd)
        for step in range(1, iterations + 1):
            ex, ey = agent_id * 100 + step, agent_id * 200 + step
            try:
                post_mouse_move(ex, ey, hwnd=hwnd, session_id=sid)
                if get_agent_cursor_position(sid) != (ex, ey):
                    errors.append(f"Agente {sid} passo {step}: divergência")
                post_mouse_click(hwnd=hwnd, session_id=sid)
                res = execute_computer_action("computer_get_agent_cursor", {"session_id": sid})
                if not res.get("success") or res["data"]["x"] != ex or res["data"]["y"] != ey:
                    errors.append(f"Consulta MCP falhou para {sid}: {res}")
            except Exception as exc:
                errors.append(f"Exceção no agente {sid}: {exc}")

    try:
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [threading.Thread(target=_agent_worker, args=(i,)) for i in range(num_agents)]
            for t in threads: t.start()
            for t in threads:
                t.join(timeout=10.0)
                if t.is_alive(): errors.append("Timeout / Deadlock detectado em thread de agente")
        assert not errors, f"Erros durante estresse multithread: {errors}"
        for i in range(num_agents):
            sid = f"agent_stress_{i}"
            assert get_agent_cursor_position(sid) == (i * 100 + iterations, i * 200 + iterations)
    finally:
        safety_gate.revoke("Fim do estresse de 12 agentes")


def test_stress_cursor_lock_high_contention_no_deadlock(reset_safety_gate: None, assigned_windows: None) -> None:
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
            for t in threads: t.start()
            for t in threads:
                t.join(timeout=8.0)
                assert not t.is_alive(), "Deadlock detectado em _cursor_lock sob alta contenção"
        assert not errors, f"Exceções sob contenção: {errors}"
    finally:
        safety_gate.revoke("Fim do teste de contenção de lock")


def test_edge_case_session_identifiers_and_isolation(reset_safety_gate: None, assigned_windows: None) -> None:
    """Verifica comportamento adversarial com session_ids nulos, vazios e especiais."""
    safety_gate.authorize()
    try:
        window_assignments.assign("default", 3000)
        post_mouse_move(11, 22, hwnd=3000, session_id=None)
        assert get_agent_cursor_position("default") == (11, 22)
        post_mouse_move(33, 44, hwnd=3000, session_id="")
        assert get_agent_cursor_position("default") == (33, 44)
        post_mouse_move(55, 66, hwnd=3000, session_id="   ")
        assert get_agent_cursor_position("default") == (55, 66)
        window_assignments.assign("agente_especial_🌟", 3001)
        post_mouse_move(77, 88, hwnd=3001, session_id="agente_especial_🌟")
        assert get_agent_cursor_position("agente_especial_🌟") == (77, 88)
    finally:
        safety_gate.revoke("Fim do teste de session_id edge cases")


def test_stress_physical_cursor_remains_untouched(reset_safety_gate: None, assigned_windows: None) -> None:
    """Garante que nenhum dos comandos concorrentes move o cursor físico do Windows."""
    safety_gate.authorize()
    try:
        cur_initial, num_agents = get_cursor_position(), 10
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [
                threading.Thread(
                    target=lambda i: [post_mouse_move(i * 15, i * 25, hwnd=4000 + i, session_id=f"phy_test_{i}") for _ in range(5)],
                    args=(i,)
                ) for i in range(num_agents)
            ]
            for i in range(num_agents): window_assignments.assign(f"phy_test_{i}", 4000 + i)
            for t in threads: t.start()
            for t in threads: t.join(timeout=5.0)
        cur_final = get_cursor_position()
        assert abs(cur_final[0] - cur_initial[0]) <= 5 and abs(cur_final[1] - cur_initial[1]) <= 5
    finally:
        safety_gate.revoke("Fim do teste de não invasão física")
