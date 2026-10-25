"""Testes unitários para o MessageBuffer, focando no método push e comportamentos correlatos."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.message_buffer import MessageBuffer


class TestMessageBufferPush(unittest.TestCase):
    """Suíte de testes para o método push e gerenciamento de capacidade do MessageBuffer."""

    def test_push_default_parameters(self) -> None:
        """Testa push com parâmetros padrão de TTL e geração de ID automático."""
        buffer = MessageBuffer(max_capacity=10, default_ttl=15.0)
        payload = {"action": "click", "x": 100, "y": 200}
        msg = buffer.push(payload)

        self.assertEqual(len(buffer), 1)
        self.assertEqual(msg.payload, payload)
        self.assertEqual(msg.ttl_seconds, 15.0)
        self.assertIsNotNone(msg.id)
        self.assertIsInstance(msg.id, str)
        self.assertGreater(len(msg.id), 0)

    def test_push_custom_ttl(self) -> None:
        """Testa push especificando um tempo de vida (TTL) customizado."""
        buffer = MessageBuffer(default_ttl=15.0)
        msg = buffer.push("payload_teste", ttl_seconds=5.0)

        self.assertEqual(msg.ttl_seconds, 5.0)
        self.assertEqual(msg.payload, "payload_teste")

    def test_push_custom_msg_id(self) -> None:
        """Testa push especificando um ID de mensagem customizado."""
        buffer = MessageBuffer()
        custom_id = "msg-custom-123"
        msg = buffer.push({"data": "info"}, msg_id=custom_id)

        self.assertEqual(msg.id, custom_id)
        self.assertEqual(msg.ttl_seconds, 15.0)

    def test_push_custom_ttl_and_msg_id(self) -> None:
        """Testa push com TTL e ID de mensagem customizados em conjunto."""
        buffer = MessageBuffer(default_ttl=10.0)
        custom_id = "msg-custom-456"
        msg = buffer.push("payload_combo", ttl_seconds=2.5, msg_id=custom_id)

        self.assertEqual(msg.id, custom_id)
        self.assertEqual(msg.ttl_seconds, 2.5)

    def test_push_overflow_eviction(self) -> None:
        """Verifica se o push descarta a mensagem mais antiga quando a capacidade máxima é excedida."""
        buffer = MessageBuffer(max_capacity=2)
        m1 = buffer.push("msg_1")
        m2 = buffer.push("msg_2")
        m3 = buffer.push("msg_3")

        self.assertEqual(len(buffer), 2)
        drained = buffer.drain()
        self.assertEqual(len(drained), 2)
        self.assertEqual(drained[0].id, m2.id)
        self.assertEqual(drained[1].id, m3.id)


if __name__ == "__main__":
    unittest.main()
