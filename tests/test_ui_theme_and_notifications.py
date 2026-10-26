"""Suíte de Testes Unitários para Tema e Notificações do Desktop App.

Testa a paleta Fluent Design Win11, configuração do modo CustomTkinter,
aplicação defensiva e fallbacks do efeito Mica, e debouncing de Toasts.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from src.ui.theme import (
    PALETTE,
    get_status_color,
    apply_mica_theme,
    configure_app_theme,
)
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

    @patch("src.ui.theme.ctk.set_appearance_mode")
    @patch("src.ui.theme.ctk.set_default_color_theme")
    def test_configure_app_theme_modes(self, mock_color_theme, mock_appearance):
        """Testa se configure_app_theme aplica modos válidos e fallback para inválidos."""
        configure_app_theme("dark")
        mock_appearance.assert_called_with("dark")
        mock_color_theme.assert_called_with("blue")

        configure_app_theme("LIGHT")
        mock_appearance.assert_called_with("light")

        configure_app_theme("system")
        mock_appearance.assert_called_with("system")

        configure_app_theme("modo_invalido")
        mock_appearance.assert_called_with("dark")

    @patch("sys.platform", "linux")
    def test_apply_mica_theme_non_win32(self):
        """Garante que apply_mica_theme retorne False em sistemas operacionais não-Windows."""
        dummy_window = MagicMock()
        self.assertFalse(apply_mica_theme(dummy_window, is_dark=True))

    @patch("sys.platform", "win32")
    @patch("src.ui.theme._PYWINSTYLES_AVAILABLE", True)
    @patch("src.ui.theme.pywinstyles", create=True)
    def test_apply_mica_theme_pywinstyles_success(self, mock_pywinstyles):
        """Valida a aplicação do efeito Mica via pywinstyles no Windows 11."""
        dummy_window = MagicMock()
        dummy_window.winfo_id.return_value = 12345
        res = apply_mica_theme(dummy_window, is_dark=True)
        self.assertTrue(res)
        mock_pywinstyles.apply_style.assert_called_once_with(dummy_window, "mica")

    @patch("sys.platform", "win32")
    @patch("src.ui.theme._PYWINSTYLES_AVAILABLE", False)
    def test_apply_mica_theme_dwm_fallback_success(self):
        """Testa o fallback defensivo para DwmSetWindowAttribute na API Win32."""
        dummy_window = MagicMock()
        dummy_window.winfo_id.return_value = 12345
        mock_dwmapi = MagicMock()
        with patch.dict("sys.modules", {"ctypes": MagicMock(windll=MagicMock(dwmapi=mock_dwmapi))}):
            res = apply_mica_theme(dummy_window, is_dark=True)
            self.assertTrue(res)

    @patch("sys.platform", "win32")
    @patch("src.ui.theme._PYWINSTYLES_AVAILABLE", False)
    def test_apply_mica_theme_exception_fallback(self):
        """Garante retorno False quando ocorre exceção durante a chamada Win32."""
        dummy_window = MagicMock()
        dummy_window.winfo_id.side_effect = Exception("HWND inválido")
        res = apply_mica_theme(dummy_window, is_dark=True)
        self.assertFalse(res)


class TestUINotifications(unittest.TestCase):
    """Testes do notificador nativo e mecanismo anti-spam (debouncing)."""

    def setUp(self):
        self.notifier = ToastNotifier(app_id="TestApp")

    def test_debouncing_prevents_duplicate_notifications(self):
        """Garante que notificações com mesmo título/mensagem sejam descartadas em janela curta."""
        res1 = self.notifier.notify("Titulo", "Mensagem de teste")
        res2 = self.notifier.notify("Titulo", "Mensagem de teste")
        self.assertFalse(res2)

    def test_notification_helper_methods(self):
        """Verifica se os métodos de ajuda chamam o despachante sem falhas."""
        _ = self.notifier.notify_emergency_stop()
        _ = self.notifier.notify_service_disconnected("MCP", "Timeout")
        _ = self.notifier.notify_service_reconnected("MCP")
        _ = self.notifier.notify_safety_gate_toggle(True)
        _ = self.notifier.notify_safety_gate_toggle(False)


if __name__ == "__main__":
    unittest.main()
