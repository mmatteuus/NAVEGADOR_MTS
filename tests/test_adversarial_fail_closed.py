"""Testes Adversariais de Trava Fail-Closed (Default-Deny) do Computer Use.

Validações rigorosas de segurança:
- Rejeição mandatória de qualquer tentativa de clique, movimento, digitação ou screenshot.
- Validação sob inputs anômalos e parâmetros maliciosos.
- Teste de estresse com 30 threads simultâneas em corrida contra a trava.
"""

from __future__ import annotations
import concurrent.futures
import pytest
from src.computer.safety_gate import safety_gate, SecurityGateError
from src.computer import (
    move_mouse, click_mouse, drag_mouse, scroll_mouse,
    type_text, press_key, capture_screen, execute_computer_action
)


def test_adversarial_all_direct_calls_blocked_unauthorized(reset_safety_gate):
    """Testa que todas as chamadas diretas são bloqueadas quando não autorizado."""
    assert not safety_gate.is_authorized()
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        move_mouse(500, 500, smooth=False)
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        click_mouse("right", double=True)
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        drag_mouse(10, 10, 100, 100)
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        scroll_mouse(delta_y=100, delta_x=50)
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        type_text("Tentativa invasora de digitação")
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        press_key("enter", modifiers=["ctrl", "alt"])
    with pytest.raises(SecurityGateError, match="ERRO_SEGURANCA"):
        capture_screen(format="png")


def test_adversarial_dispatcher_rejection_matrix(reset_safety_gate):
    """Verifica a matriz de rejeição do despachante universal sob estado bloqueado."""
    actions = [
        ("computer_mouse_click", {"button": "left"}),
        ("click", {"button": "right"}),
        ("computer_mouse_move", {"x": 100, "y": 200}),
        ("move", {"x": 0, "y": 0}),
        ("computer_mouse_drag", {"startX": 1, "startY": 1, "endX": 10, "endY": 10}),
        ("drag", {"startX": 0, "startY": 0, "endX": 5, "endY": 5}),
        ("computer_mouse_scroll", {"deltaY": 120}),
        ("scroll", {"deltaY": -120}),
        ("computer_keyboard_type", {"text": "Ataque"}),
        ("type", {"text": "Injeção"}),
        ("computer_key_press", {"key": "esc"}),
        ("press_key", {"key": "f4", "modifiers": ["alt"]}),
        ("computer_screenshot", {"format": "jpeg"}),
        ("screenshot", {}),
    ]
    for act, params in actions:
        res = execute_computer_action(act, params)
        assert res["success"] is False, f"Ação '{act}' não foi rejeitada!"
        assert res.get("isSecurityBlock") is True, f"Ação '{act}' sem flag isSecurityBlock!"
        assert "ERRO_SEGURANCA" in res["error"]


def test_adversarial_malformed_inputs_behavior(reset_safety_gate):
    """Garante que todas as ações com inputs vazios/malformados sofrem bloqueio Fail-Closed."""
    assert not safety_gate.is_authorized()

    # Todas as ações alcançam o SafetyGate com params vazios {} antes de qualquer indexação
    all_actions = [
        "computer_mouse_click", "computer_screenshot", "computer_mouse_scroll",
        "computer_mouse_move", "computer_mouse_drag", "computer_keyboard_type",
        "computer_key_press"
    ]
    for act in all_actions:
        res = execute_computer_action(act, {})
        assert res["success"] is False
        assert res.get("isSecurityBlock") is True
        assert "ERRO_SEGURANCA" in res["error"]

    # Histórico de auditoria deve conter todas as tentativas bloqueadas
    history = safety_gate.get_audit_history()
    blocked_actions = {e["action"] for e in history if not e["success"]}
    for act in all_actions:
        assert act in blocked_actions


def test_adversarial_multithreaded_race_condition_fail_closed(reset_safety_gate):
    """Estressa a trava com 30 threads simultâneas tentando furar a política."""
    assert not safety_gate.is_authorized()
    num_threads = 30
    results = []

    def try_unauthorized_action(idx: int):
        act = "computer_mouse_click" if idx % 2 == 0 else "computer_screenshot"
        return execute_computer_action(act, {"button": "left"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(try_unauthorized_action, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    assert len(results) == num_threads
    for r in results:
        assert r["success"] is False
        assert r.get("isSecurityBlock") is True
        assert "ERRO_SEGURANCA" in r["error"]

    history = safety_gate.get_audit_history()
    # Pelo menos 30 tentativas foram registradas na auditoria como falha
    failed_audits = [e for e in history if not e["success"]]
    assert len(failed_audits) >= num_threads
