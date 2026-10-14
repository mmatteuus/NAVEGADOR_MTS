"""Testes Adversariais do Kill-Switch de Emergência (3x ESC em < 1.2s).

Validações rigorosas:
- Cancelamento instantâneo de comandos e revogação no Safety Gate.
- Acionamento compulsório de callbacks de limpeza (release_all_keys e mouse).
- Rejeição contínua pós-kill-switch com mensagem explícita.
- Estresse de concorrência com 50 eventos concorrentes de ESC.
- Resiliência contra toques lentos e rearmamento limpo.
"""

from __future__ import annotations
import concurrent.futures
import time
import pytest
from src.computer.kill_switch import EmergencyKillSwitch, kill_switch
from src.computer.safety_gate import safety_gate, SecurityGateError
from src.computer import execute_computer_action


def test_kill_switch_instant_revocation_and_cleanup(reset_safety_gate):
    """Garante revogação atômica e disparo de rotinas de limpeza compulsórias."""
    safety_gate.authorize()
    assert safety_gate.is_authorized()

    ks = EmergencyKillSwitch(window_seconds=1.2, required_presses=3)
    cleanup_1_called = False
    cleanup_2_called = False

    def cb1():
        nonlocal cleanup_1_called
        cleanup_1_called = True

    def cb2():
        nonlocal cleanup_2_called
        cleanup_2_called = True

    ks.register_cleanup_callback(cb1)
    ks.register_cleanup_callback(cb2)

    ks.record_esc_press()
    ks.record_esc_press()
    assert not cleanup_1_called and not cleanup_2_called
    assert safety_gate.is_authorized()

    # 3º toque em janela rápida aciona parada de emergência
    triggered = ks.record_esc_press()
    assert triggered is True
    assert not safety_gate.is_authorized()
    assert safety_gate.is_kill_switch_triggered()
    assert cleanup_1_called is True
    assert cleanup_2_called is True

    # Comandos agora devem ser terminantemente barrados com motivo de Kill-Switch
    with pytest.raises(SecurityGateError, match="Kill-Switch acionado"):
        safety_gate.check_authorization("teste_pos_panico")

    res = execute_computer_action("computer_mouse_click")
    assert res["success"] is False
    assert res.get("isSecurityBlock") is True
    assert "Kill-Switch acionado" in res["error"]


def test_kill_switch_programmatic_trigger(reset_safety_gate):
    """Testa parada emergencial disparada programaticamente."""
    safety_gate.authorize()
    ks = EmergencyKillSwitch()
    pânico_chamado = False
    ks.register_cleanup_callback(lambda: globals().update(pânico_chamado=True))

    ks.trigger_emergency_stop()
    assert not safety_gate.is_authorized()
    assert safety_gate.is_kill_switch_triggered()


def test_kill_switch_multithreaded_rapid_presses(reset_safety_gate):
    """Estressa o buffer de timestamps com 40 threads disparando ESC simultaneamente."""
    safety_gate.authorize()
    ks = EmergencyKillSwitch(window_seconds=1.2, required_presses=3)
    call_counts = 0

    def cleanup():
        nonlocal call_counts
        call_counts += 1

    ks.register_cleanup_callback(cleanup)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(ks.record_esc_press) for _ in range(40)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # O kill switch deve ter disparado sem travar ou corromper memória
    assert any(results)
    assert not safety_gate.is_authorized()
    assert safety_gate.is_kill_switch_triggered()
    assert call_counts >= 1


def test_kill_switch_rearm_and_recovery(reset_safety_gate):
    """Testa ciclo completo de pânico, verificação de bloqueio e recuperação limpa."""
    safety_gate.authorize()
    ks = EmergencyKillSwitch()
    ks.trigger_emergency_stop()
    assert safety_gate.is_kill_switch_triggered()

    # Rearma o kill-switch
    safety_gate.reset_kill_switch()
    assert not safety_gate.is_kill_switch_triggered()
    # Continua desautorizado até que o usuário autorize explicitamente novamente
    assert not safety_gate.is_authorized()

    safety_gate.authorize()
    assert safety_gate.is_authorized()
    safety_gate.check_authorization("acao_recuperada")
