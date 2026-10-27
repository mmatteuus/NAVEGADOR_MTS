"""Suíte de Testes Unitários dos Componentes do Motor de Resiliência."""

from __future__ import annotations

import os
import socket
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.heartbeat import HeartbeatConfig, HeartbeatManager
from src.core.message_buffer import MessageBuffer
from src.core.resilience import ExponentialBackoff, configure_socket_reuse
from src.core.supervisor import ProcessSupervisor


class TestResilienceEngine(unittest.TestCase):
    """Validação das camadas do motor de resiliência e auto-recuperação."""

    def test_message_buffer_fifo_and_ttl(self) -> None:
        """Valida que o buffer circular respeita ordem FIFO e expiração de TTL."""
        buffer = MessageBuffer(max_capacity=5, default_ttl=0.1)
        buffer.push({"cmd": "click_1"})
        buffer.push({"cmd": "click_2"})
        self.assertEqual(len(buffer), 2)
        popped = buffer.pop()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.payload["cmd"], "click_1")
        time.sleep(0.12)
        self.assertEqual(buffer.cleanup_expired(), 1)
        self.assertTrue(buffer.is_empty())

    def test_message_buffer_circular_capacity(self) -> None:
        """Verifica se o buffer circular descarta os mais antigos ao estourar o limite."""
        buffer = MessageBuffer(max_capacity=3, default_ttl=15.0)
        for i in range(5):
            buffer.push({"id": i})
        self.assertEqual(len(buffer), 3)
        msgs = buffer.drain()
        self.assertEqual([m.payload["id"] for m in msgs], [2, 3, 4])

    @patch("time.time", return_value=1700000000.123)
    def test_create_ping_payload_structure_and_state(self, mock_time: MagicMock) -> None:
        """Garante estrutura do payload de ping, timestamp em ms e estado."""
        manager = HeartbeatManager()
        self.assertFalse(manager._waiting_pong)
        self.assertEqual(manager._last_ping_sent, 0.0)
        payload = manager.create_ping_payload()
        self.assertEqual(payload, {"type": "ping", "timestamp": 1700000000123})
        self.assertTrue(manager._waiting_pong)
        self.assertEqual(manager._last_ping_sent, 1700000000.123)

    @patch("time.time")
    def test_record_pong_latency_and_state_mutation(self, mock_time: MagicMock) -> None:
        """Valida cálculo de latência, zeragem de falhas e restauração de saúde no record_pong."""
        manager = HeartbeatManager()
        manager._waiting_pong = True
        manager._missed_pings = 2
        manager._is_healthy = False

        # Latência normal e mutação de estado
        mock_time.return_value = 100.0
        manager.create_ping_payload()
        mock_time.return_value = 100.050
        latency = manager.record_pong()

        self.assertAlmostEqual(latency, 50.0)
        self.assertAlmostEqual(manager.latency_ms, 50.0)
        self.assertFalse(manager._waiting_pong)
        self.assertEqual(manager.missed_count, 0)
        self.assertTrue(manager.is_healthy)
        self.assertEqual(manager._last_pong_received, 100.050)

        # Record pong sem ping prévio (_last_ping_sent == 0)
        manager.reset()
        mock_time.return_value = 200.0
        self.assertEqual(manager.record_pong(), 0.0)
        self.assertEqual(manager._last_pong_received, 200.0)

        # Tempo retrocedido (clamp max(0.0, ...))
        manager._last_ping_sent = 300.0
        mock_time.return_value = 290.0
        self.assertEqual(manager.record_pong(), 0.0)

    def test_heartbeat_timeout_and_disconnection_trigger(self) -> None:
        """Verifica a detecção de queda após atingir o limite de pings perdidos."""
        falhas = []
        cfg = HeartbeatConfig(interval_seconds=1.0, timeout_seconds=0.05, max_missed_pings=2)
        manager = HeartbeatManager(config=cfg, on_failure_callback=falhas.append)
        manager.create_ping_payload()
        time.sleep(0.06)
        manager.check_health()
        self.assertEqual(manager.missed_count, 1)
        manager.create_ping_payload()
        time.sleep(0.06)
        self.assertFalse(manager.check_health())
        self.assertEqual(len(falhas), 1)

    def test_exponential_backoff_progression_and_ceiling(self) -> None:
        """Valida que o recuo exponencial respeita a escala (0.5s -> 5s teto)."""
        backoff = ExponentialBackoff(initial=0.5, multiplier=2.0, max_delay=5.0, jitter_factor=0.0)
        delays = [backoff.next_delay() for _ in range(5)]
        self.assertEqual(delays, [0.5, 1.0, 2.0, 4.0, 5.0])
        for _ in range(3):
            self.assertLessEqual(backoff.next_delay(), 5.0)
        backoff.reset()
        self.assertEqual(backoff.next_delay(), 0.5)

    def test_socket_reuse_addr_configuration(self) -> None:
        """Verifica a aplicação de SO_REUSEADDR para eliminar TIME_WAIT em sockets."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            configure_socket_reuse(sock)
            self.assertNotEqual(sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0)
        finally:
            sock.close()

    def test_process_supervisor_lifecycle_and_restart(self) -> None:
        """Testa inicialização, métricas, reinício e encerramento limpo."""
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
        supervisor = ProcessSupervisor(command=cmd, name="worker_teste", restart_delay=0.1)
        self.assertTrue(supervisor.start())
        self.assertTrue(supervisor.is_alive())
        self.assertTrue(supervisor.get_metrics()["alive"])
        start_t = time.time()
        self.assertTrue(supervisor.restart(reason="Teste unitário"))
        self.assertLess(time.time() - start_t, 1.0)
        self.assertTrue(supervisor.is_alive())
        supervisor.terminate_tree()
        self.assertFalse(supervisor.is_alive())


if __name__ == "__main__":
    unittest.main()
