"""Suíte de Testes da Trava de Segurança e Kill-Switch (Safety Gate).

Valida a política de Fail-Closed (Default-Deny), a autorização explícita
e o acionamento emergencial pelo Kill-Switch de 3 toques em ESC (<1.2s).
"""

from __future__ import annotations

import time
import pytest
from src.computer.kill_switch import EmergencyKillSwitch
from src.computer.safety_gate import SafetyGate, SecurityGateError


def test_safety_gate_default_deny(reset_safety_gate: None) -> None:
    """Verifica que o sistema inicia obrigatoriamente bloqueado por padrão."""
    gate = SafetyGate()
    assert not gate.is_authorized(), "O SafetyGate deve iniciar desautorizado (Default-Deny)."
    with pytest.raises(SecurityGateError) as exc_info:
        gate.check_authorization("mover_mouse")
    assert "ERRO_SEGURANCA" in str(exc_info.value)


def test_safety_gate_authorization_lifecycle(reset_safety_gate: None) -> None:
    """Testa a concessão e revogação manual de autorização pelo usuário."""
    gate = SafetyGate()
    notifications: list[tuple[bool, str]] = []
    gate.add_listener(lambda auth, reason: notifications.append((auth, reason)))

    gate.authorize()
    assert gate.is_authorized(), "Após authorize(), o estado deve ser True."
    gate.check_authorization("clicar_tela")  # Não deve levantar exceção

    gate.revoke("Ação manual do usuário")
    assert not gate.is_authorized(), "Após revoke(), o estado deve retornar a False."
    assert len(notifications) >= 2


def test_kill_switch_triple_esc_trigger(reset_safety_gate: None) -> None:
    """Valida o acionamento do Kill-Switch ao detectar 3 toques em ESC em < 1.2s."""
    gate = SafetyGate()
    gate.authorize()
    assert gate.is_authorized()

    ks = EmergencyKillSwitch(window_seconds=1.2, required_presses=3)
    cleanup_called = False
    ks.register_cleanup_callback(lambda: globals().update(cleanup_called=True))

    # 1º e 2º toque em ESC não disparam o kill-switch
    assert not ks.record_esc_press()
    assert not ks.record_esc_press()
    assert gate.is_authorized()

    # 3º toque em menos de 1.2s aciona a emergência
    assert ks.record_esc_press()
    assert not gate.is_authorized(), "Kill-Switch deve revogar a autorização na hora."
    assert gate.is_kill_switch_triggered(), "Flag de Kill-Switch deve estar ativa."


def test_kill_switch_slow_esc_ignored(reset_safety_gate: None) -> None:
    """Verifica que 3 toques lentos (acima da janela de 1.2s) NÃO disparam o Kill-Switch."""
    gate = SafetyGate()
    gate.authorize()

    ks = EmergencyKillSwitch(window_seconds=0.2, required_presses=3)
    assert not ks.record_esc_press()
    time.sleep(0.25)  # Expira a janela temporal
    assert not ks.record_esc_press()
    time.sleep(0.25)
    assert not ks.record_esc_press()

    assert gate.is_authorized(), "Toques espaçados não devem acionar o Kill-Switch."
    assert not gate.is_kill_switch_triggered()


def test_kill_switch_reset_rearm(reset_safety_gate: None) -> None:
    """Verifica o rearmamento do sistema após acionamento do Kill-Switch."""
    gate = SafetyGate()
    gate.authorize()
    gate.revoke("KILL_SWITCH_TEST")
    assert gate.is_kill_switch_triggered()

    gate.reset_kill_switch()
    assert not gate.is_kill_switch_triggered(), "Kill-Switch deve ser desarmado."


def test_safety_gate_audit_history(reset_safety_gate: None) -> None:
    """Verifica o registro em log de auditoria das ações permitidas e negadas."""
    gate = SafetyGate()
    gate.authorize()
    gate.check_authorization("teste_audit_ok")
    history = gate.get_audit_history()
    assert any(entry["action"] == "teste_audit_ok" and entry["success"] for entry in history)
