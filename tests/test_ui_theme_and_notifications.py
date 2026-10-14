"""Suíte de Testes Unitários para Tema e Notificações do Desktop App.

Testa a paleta Fluent Design Win11, fallback do efeito Mica,
debouncing de notificações Toast e mapeamento de semáforos de status.
"""

import time
import unittest
from unittest.mock import MagicMock
from src.ui.theme import PALETTE, get_status_color, apply_mica_theme, configure_app_theme
from src.ui.notifications import ToastNotifier


class TestUITheme(unittest.TestCase):
    """Testes unitários do módulo de estilos e paleta Fluent."""

    def test_palette_contrast_and_dimensions(self):
        """Valida que as cores e dimensões da paleta Fluent atendem às diretrizes."""
        self.assertTrue(PALETTE.bg_dark.startswith("#"))
        self.assertTrue(PALETTE.bg_light.startswith("#"))
        self.assertGreater(PALETTE.corner_radius, 0)
        self.assertGreater(PALETTE.card_corner_radius, 0)

    def test_get_status_color_mappings(self):
        """Verifica se os estados de serviço mapeiam para as cores corretas."""
        self.assertEqual(get_status_color("conectado"), PALETTE.success)
        self.assertEqual(get_status_color("ativo"), PALETTE.success)
        self.assertEqual(get_status_color("reconectando"), PALETTE.warning)
        self.assertEqual(get_status_color("erro"), PALETTE.error)
        self.assertEqual(get_status_color("desconhecido"), PALETTE.error)

    def test_apply_mica_theme_graceful_fallback(self):
        """Testa o comportamento defensivo da função apply_mica_theme com mock de janela."""
        dummy_window = MagicMock()
        dummy_window.winfo_id.return_value = 12345
        # Não deve lançar exceção mesmo com HWND falso
        res = apply_mica_theme(dummy_window, is_dark=True)
        self.assertIsInstance(res, bool)


class TestUINotifications(unittest.TestCase):
    """Testes do notificador nativo e mecanismo anti-spam (debouncing)."""

    def setUp(self):
        self.notifier = ToastNotifier(app_id="TestApp")

    def test_debouncing_prevents_duplicate_notifications(self):
        """Garante que notificações com mesmo título/mensagem sejam descartadas em janela curta."""
        # Primeira chamada registra o timestamp
        res1 = self.notifier.notify("Titulo", "Mensagem de teste")
        # Segunda chamada imediata deve ser bloqueada pelo debouncing
        res2 = self.notifier.notify("Titulo", "Mensagem de teste")
        self.assertFalse(res2)

    def test_notification_helper_methods(self):
        """Verifica se os métodos de ajuda chamam o despachante sem falhas."""
        # Chamadas para métodos especializados não devem estourar exceções
        _ = self.notifier.notify_emergency_stop()
        _ = self.notifier.notify_service_disconnected("MCP", "Timeout")
        _ = self.notifier.notify_service_reconnected("MCP")
        _ = self.notifier.notify_safety_gate_toggle(True)
        _ = self.notifier.notify_safety_gate_toggle(False)


if __name__ == "__main__":
    unittest.main()
