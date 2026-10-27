"""Testes unitários focados na validação da saúde do HeartbeatManager (check_health)."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.heartbeat import HeartbeatConfig, HeartbeatManager


class TestHeartbeatCheckHealth(unittest.TestCase):
    """Suíte de testes para o método check_health do HeartbeatManager."""

    def test_check_health_when_idle(self) -> None:
        """Garante que check_health retorna True e não incrementa falhas sem pings pendentes."""
        manager = HeartbeatManager()
        is_healthy = manager.check_health(current_time=100.0)
        self.assertTrue(is_healthy)
        self.assertEqual(manager.missed_count, 0)

    def test_check_health_within_timeout_seconds(self) -> None:
        """Verifica que pings dentro da janela de timeout mantêm a conexão saudável."""
        manager = HeartbeatManager(config=HeartbeatConfig(timeout_seconds=2.0))
        manager._last_ping_sent = 100.0
        manager._waiting_pong = True

        # Decorrido 1.5s <= 2.0s timeout
        is_healthy = manager.check_health(current_time=101.5)
        self.assertTrue(is_healthy)
        self.assertEqual(manager.missed_count, 0)
        self.assertTrue(manager._waiting_pong)

    def test_check_health_timeout_exceeded_single_ping(self) -> None:
        """Valida incremento de missed_pings ao ultrapassar o timeout de um ping."""
        manager = HeartbeatManager(config=HeartbeatConfig(timeout_seconds=2.0, max_missed_pings=2))
        manager._last_ping_sent = 100.0
        manager._waiting_pong = True

        # Decorrido 2.5s > 2.0s timeout
        is_healthy = manager.check_health(current_time=102.5)
        self.assertTrue(is_healthy)
        self.assertEqual(manager.missed_count, 1)
        self.assertFalse(manager._waiting_pong)

    def test_check_health_max_missed_pings_triggers_failure_callback(self) -> None:
        """Garante transição para não saudável e disparo de callback ao atingir o limite."""
        failures: list[str] = []
        cfg = HeartbeatConfig(timeout_seconds=2.0, max_missed_pings=2)
        manager = HeartbeatManager(config=cfg, on_failure_callback=failures.append)

        # Primeiro ping sem resposta
        manager._last_ping_sent = 100.0
        manager._waiting_pong = True
        manager.check_health(current_time=102.5)

        # Segundo ping sem resposta
        manager._last_ping_sent = 103.0
        manager._waiting_pong = True
        is_healthy = manager.check_health(current_time=105.5)

        self.assertFalse(is_healthy)
        self.assertFalse(manager.is_healthy)
        self.assertEqual(manager.missed_count, 2)
        self.assertEqual(len(failures), 1)
        self.assertIn("Falha de Heartbeat: 2 pings consecutivos sem resposta", failures[0])

    def test_check_health_callback_idempotency_when_unhealthy(self) -> None:
        """Garante que o callback de falha só é acionado uma vez ao permanecer não saudável."""
        failures: list[str] = []
        cfg = HeartbeatConfig(timeout_seconds=2.0, max_missed_pings=1)
        manager = HeartbeatManager(config=cfg, on_failure_callback=failures.append)

        manager._last_ping_sent = 100.0
        manager._waiting_pong = True
        manager.check_health(current_time=102.5)
        self.assertEqual(len(failures), 1)

        # Chamada subsequente no mesmo estado não saudável
        is_healthy = manager.check_health(current_time=103.0)
        self.assertFalse(is_healthy)
        self.assertEqual(len(failures), 1)

    def test_check_health_without_failure_callback(self) -> None:
        """Garante que check_health funciona sem exceções quando on_failure_callback é None."""
        cfg = HeartbeatConfig(timeout_seconds=2.0, max_missed_pings=1)
        manager = HeartbeatManager(config=cfg, on_failure_callback=None)

        manager._last_ping_sent = 100.0
        manager._waiting_pong = True
        is_healthy = manager.check_health(current_time=102.5)

        self.assertFalse(is_healthy)
        self.assertFalse(manager.is_healthy)

    @patch("time.time", return_value=105.0)
    def test_check_health_uses_system_time_when_none(self, mock_time: MagicMock) -> None:
        """Garante uso de time.time() quando current_time não é fornecido."""
        manager = HeartbeatManager(config=HeartbeatConfig(timeout_seconds=2.0))
        manager._last_ping_sent = 100.0
        manager._waiting_pong = True

        manager.check_health()  # current_time=None por padrão
        mock_time.assert_called_once()
        self.assertEqual(manager.missed_count, 1)

    def test_check_health_recovery_after_pong(self) -> None:
        """Valida que record_pong restaura a saúde e o check_health volta a retornar True."""
        cfg = HeartbeatConfig(timeout_seconds=2.0, max_missed_pings=1)
        manager = HeartbeatManager(config=cfg)

        manager._last_ping_sent = 100.0
        manager._waiting_pong = True
        manager.check_health(current_time=102.5)
        self.assertFalse(manager.is_healthy)

        # Recebimento de pong restaura a saúde
        manager.record_pong()
        self.assertTrue(manager.is_healthy)
        self.assertEqual(manager.missed_count, 0)
        self.assertTrue(manager.check_health(current_time=110.0))


if __name__ == "__main__":
    unittest.main()
