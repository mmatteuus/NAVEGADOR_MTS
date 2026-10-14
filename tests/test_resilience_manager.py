"""Suíte de Testes para o Orquestrador ResilienceManager e Máquina de Estados.

Valida as transições de ciclo de vida (STOPPED -> CONNECTED -> DEGRADED -> RECOVERING),
o enfileiramento resiliente no MessageBuffer durante instabilidade e a auto-cura em <= 5s.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.message_buffer import MessageBuffer
from src.core.resilience import ConnectionState, ResilienceManager


class TestResilienceManager(unittest.TestCase):
    """Testes da máquina de estados finita e despacho no retorno do sinal."""

    def test_state_transitions_and_callbacks(self) -> None:
        """Verifica as mudanças de estado e o disparo correto do callback."""
        historico_transicoes = []

        def rastreador(antigo: ConnectionState, novo: ConnectionState, motivo: str) -> None:
            historico_transicoes.append((antigo, novo, motivo))

        manager = ResilienceManager(on_state_change=rastreador)
        self.assertEqual(manager.state, ConnectionState.STOPPED)

        # Transição para CONNECTING
        manager.transition_to(ConnectionState.CONNECTING, "Iniciando WebSocket")
        self.assertEqual(manager.state, ConnectionState.CONNECTING)

        # Transição para CONNECTED
        msgs = manager.handle_connected()
        self.assertEqual(manager.state, ConnectionState.CONNECTED)
        self.assertEqual(len(msgs), 0)

        # Registra desconexão -> deve passar para DEGRADED e depois RECOVERING
        delay = manager.handle_disconnect("Oscilação de rede Wi-Fi")
        self.assertLessEqual(delay, 5.0)
        self.assertEqual(manager.state, ConnectionState.RECOVERING)

        # Verifica histórico de transições
        self.assertGreaterEqual(len(historico_transicoes), 4)

    def test_buffering_during_instability_and_auto_healing(self) -> None:
        """Garante que requisições sejam retidas em buffer durante queda e drenadas na volta."""
        buffer = MessageBuffer(max_capacity=10, default_ttl=15.0)
        manager = ResilienceManager(buffer=buffer)

        # Estado inicial conectado
        manager.handle_connected()
        self.assertFalse(manager.should_buffer())

        # Queda de conexão detectada
        delay = manager.handle_disconnect("Perda de ping da extensão")
        self.assertTrue(manager.should_buffer())
        self.assertLessEqual(delay, 5.0)

        # Agente tenta enviar comandos durante a instabilidade
        m1 = manager.enqueue_command({"action": "browser_click", "target": "#btn1"})
        m2 = manager.enqueue_command({"action": "browser_type", "text": "teste"})
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertEqual(len(manager.buffer), 2)

        # Conexão restabelecida: comandos devem ser drenados em ordem FIFO
        mensagens_drenadas = manager.handle_connected()
        self.assertEqual(manager.state, ConnectionState.CONNECTED)
        self.assertEqual(len(mensagens_drenadas), 2)
        self.assertEqual(mensagens_drenadas[0].payload["action"], "browser_click")
        self.assertEqual(mensagens_drenadas[1].payload["action"], "browser_type")
        self.assertTrue(manager.buffer.is_empty())


if __name__ == "__main__":
    unittest.main()
