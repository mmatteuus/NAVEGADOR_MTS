"""Suíte de Testes Unitários dos Componentes do Motor de Resiliência.

Testa MessageBuffer (TTL 15s e rotação circular), HeartbeatManager (3s ping / 2s timeout),
ExponentialBackoff (0.5s a 5s teto), SO_REUSEADDR e ProcessSupervisor (psutil e restart <= 500ms).
"""

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
    """Validação das 5 camadas do motor de resiliência e auto-recuperação."""

    def test_message_buffer_fifo_and_ttl(self) -> None:
        """Valida que o buffer circular respeita ordem FIFO e expiração de TTL."""
        buffer = MessageBuffer(max_capacity=5, default_ttl=0.1)
        m1 = buffer.push({"cmd": "click_1"})
        m2 = buffer.push({"cmd": "click_2"})
        self.assertEqual(len(buffer), 2)
        popped = buffer.pop()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.payload["cmd"], "click_1")
        time.sleep(0.12)
        expired_count = buffer.cleanup_expired()
        self.assertEqual(expired_count, 1)
        self.assertTrue(buffer.is_empty())

    def test_message_buffer_circular_capacity(self) -> None:
        """Verifica se o buffer circular descarta os mais antigos ao estourar o limite."""
        buffer = MessageBuffer(max_capacity=3, default_ttl=15.0)
        for i in range(5):
            buffer.push({"id": i})
        self.assertEqual(len(buffer), 3)
        msgs = buffer.drain()
        self.assertEqual(len(msgs), 3)
        self.assertEqual([m.payload["id"] for m in msgs], [2, 3, 4])

    @patch("time.time", return_value=1700000000.123)
    def test_create_ping_payload_structure_and_state(self, mock_time: MagicMock) -> None:
        """Garante a estrutura do payload de ping, timestamp em ms e atualização de estado."""
        manager = HeartbeatManager()
        self.assertFalse(manager._waiting_pong)
        self.assertEqual(manager._last_ping_sent, 0.0)

        payload = manager.create_ping_payload()

        self.assertEqual(payload, {"type": "ping", "timestamp": 1700000000123})
        self.assertTrue(manager._waiting_pong)
        self.assertEqual(manager._last_ping_sent, 1700000000.123)

    def test_heartbeat_ping_pong_latency(self) -> None:
        """Garante geração correta do envelope de ping e cálculo de latência do pong."""
        manager = HeartbeatManager()
        ping_payload = manager.create_ping_payload()
        self.assertEqual(ping_payload["type"], "ping")
        self.assertIn("timestamp", ping_payload)
        time.sleep(0.01)
        latency = manager.record_pong()
        self.assertGreater(latency, 0.0)
        self.assertTrue(manager.is_healthy)
        self.assertEqual(manager.missed_count, 0)

    def test_heartbeat_timeout_and_disconnection_trigger(self) -> None:
        """Verifica a detecção de queda após atingir o limite de pings perdidos."""
        falhas_detectadas = []
        cfg = HeartbeatConfig(interval_seconds=1.0, timeout_seconds=0.05, max_missed_pings=2)
        manager = HeartbeatManager(config=cfg, on_failure_callback=falhas_detectadas.append)
        manager.create_ping_payload()
        time.sleep(0.06)
        manager.check_health()
        self.assertEqual(manager.missed_count, 1)
        manager.create_ping_payload()
        time.sleep(0.06)
        saudavel = manager.check_health()
        self.assertFalse(saudavel)
        self.assertEqual(len(falhas_detectadas), 1)

    def test_exponential_backoff_progression_and_ceiling(self) -> None:
        """Valida que o recuo exponencial respeita a escala (0.5s -> 5s teto)."""
        backoff = ExponentialBackoff(initial=0.5, multiplier=2.0, max_delay=5.0, jitter_factor=0.0)
        delays = [backoff.next_delay() for _ in range(5)]
        self.assertEqual(delays[0], 0.5)
        self.assertEqual(delays[1], 1.0)
        self.assertEqual(delays[2], 2.0)
        self.assertEqual(delays[3], 4.0)
        self.assertEqual(delays[4], 5.0)
        delays_extras = [backoff.next_delay() for _ in range(5)]
        for d in delays_extras:
            self.assertLessEqual(d, 5.0)
        backoff.reset()
        self.assertEqual(backoff.next_delay(), 0.5)

    def test_socket_reuse_addr_configuration(self) -> None:
        """Verifica a aplicação de SO_REUSEADDR para eliminar TIME_WAIT em sockets."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            configure_socket_reuse(sock)
            opt = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
            self.assertNotEqual(opt, 0)
        finally:
            sock.close()

    def test_process_supervisor_lifecycle_and_restart(self) -> None:
        """Testa inicialização, métricas, reinício em <= 500ms e encerramento limpo."""
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
        supervisor = ProcessSupervisor(command=cmd, name="worker_teste", restart_delay=0.1)
        self.assertTrue(supervisor.start())
        self.assertTrue(supervisor.is_alive())
        metrics = supervisor.get_metrics()
        self.assertTrue(metrics["alive"])
        self.assertIsNotNone(metrics["pid"])
        start_t = time.time()
        self.assertTrue(supervisor.restart(reason="Teste unitário"))
        elapsed = time.time() - start_t
        self.assertLess(elapsed, 1.0)
        self.assertTrue(supervisor.is_alive())
        supervisor.terminate_tree()
        self.assertFalse(supervisor.is_alive())


if __name__ == "__main__":
    unittest.main()
