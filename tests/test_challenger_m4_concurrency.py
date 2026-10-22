"""Teste Empírico Adversarial de Concorrência e Estresse Multithread no M4.

Valida isolamento de 10+ agentes simultâneos em mouse_background.py, ausência
de deadlocks em _cursor_lock sob alta contenção e integridade de coordenadas.
"""
from __future__ import annotations
import threading
from typing import Generator
from unittest.mock import patch
import pytest
from src.computer import (
    execute_computer_action, get_agent_cursor_position,
    get_cursor_position, post_mouse_click,
    post_mouse_move, post_mouse_scroll, reset_agent_cursors,
    safety_gate,
)


@pytest.fixture(autouse=True)
def clean_cursors() -> Generator[None, None, None]:
    """Assegura isolamento limpo de cursores entre execuções de teste."""
    reset_agent_cursors()
    yield
    reset_agent_cursors()


def test_stress_12_agents_concurrent_virtual_cursors(reset_safety_gate: None) -> None:
    """Dispara 12 agentes simultâneos validando ausência de vazamento de coordenadas."""
    safety_gate.authorize()
    errors: list[str] = []
    num_agents = 12
    iterations = 20

    def _agent_worker(agent_id: int) -> None:
        sid = f"agent_stress_{agent_id}"
        for step in range(1, iterations + 1):
            expected_x = agent_id * 100 + step
            expected_y = agent_id * 200 + step
            try:
                post_mouse_move(expected_x, expected_y, session_id=sid)
                pos = get_agent_cursor_position(sid)
                if pos != (expected_x, expected_y):
                    errors.append(f"Agente {sid} passo {step}: esperado {(expected_x, expected_y)}, obteve {pos}")
                post_mouse_click(session_id=sid)
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


def test_stress_cursor_lock_high_contention_no_deadlock(reset_safety_gate: None) -> None:
    """Submete _cursor_lock a contenção agressiva com 16 threads misturando ações."""
    safety_gate.authorize()
    errors: list[Exception] = []
    num_threads = 16

    def _contention_worker(idx: int) -> None:
        sid = f"contention_agent_{idx}"
        try:
            for step in range(1, 15):
                post_mouse_move(idx * 10 + step, idx * 20 + step, session_id=sid)
                post_mouse_click(session_id=sid)
                post_mouse_scroll(delta_y=10, session_id=sid)
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


def test_edge_case_session_identifiers_and_isolation(reset_safety_gate: None) -> None:
    """Verifica comportamento adversarial com session_ids nulos, vazios e especiais."""
    safety_gate.authorize()
    try:
        post_mouse_move(11, 22, session_id=None)
        assert get_agent_cursor_position("default") == (11, 22)
        assert get_agent_cursor_position(None) == (11, 22)

        post_mouse_move(33, 44, session_id="")
        assert get_agent_cursor_position("default") == (33, 44)

        post_mouse_move(55, 66, session_id="   ")
        assert get_agent_cursor_position("default") == (55, 66)

        post_mouse_move(77, 88, session_id="agente_especial_🌟")
        assert get_agent_cursor_position("agente_especial_🌟") == (77, 88)
        assert get_agent_cursor_position("default") == (55, 66)
    finally:
        safety_gate.revoke("Fim do teste de session_id edge cases")


def test_stress_physical_cursor_remains_untouched(reset_safety_gate: None) -> None:
    """Garante que nenhum dos comandos concorrentes move o cursor físico do Windows."""
    safety_gate.authorize()
    try:
        cur_initial = get_cursor_position()
        num_agents = 10
        with patch("src.computer.mouse_background.time.sleep", return_value=None):
            threads = [
                threading.Thread(
                    target=lambda i: [post_mouse_move(i * 15, i * 25, session_id=f"phy_test_{i}") for _ in range(5)],
                    args=(i,)
                ) for i in range(num_agents)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)
        assert get_cursor_position() == cur_initial, "Cursor físico do usuário foi movido indevidamente"
    finally:
        safety_gate.revoke("Fim do teste de não invasão física")
