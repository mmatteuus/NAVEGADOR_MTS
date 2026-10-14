"""Suíte de Testes Unitários para Painéis e Janela Principal do Desktop App.

Testa a geração de ícones da bandeja, a estrutura dos painéis de Dashboard
e Configurações, a navegação da Janela Principal e as funções de autostart.
"""

import unittest
from PIL import Image
from src.ui.tray import create_tray_icon_image, SystemTrayManager
from src.ui.main_window import MainWindow
from src.ui.settings_panel import is_autostart_enabled
from src.computer.safety_gate import safety_gate


class TestUIPanelsAndWindow(unittest.TestCase):
    """Testes unitários e de integração de componentes gráficos CustomTkinter."""

    @classmethod
    def setUpClass(cls):
        """Inicializa a janela principal uma única vez para os testes da classe."""
        cls.win = MainWindow()
        cls.win.update_idletasks()
        cls.win.update()

    @classmethod
    def tearDownClass(cls):
        """Destrói a janela de teste com segurança."""
        try:
            cls.win.destroy()
        except Exception:
            pass

    def test_create_tray_icon_image(self):
        """Valida que o ícone do System Tray é gerado como imagem RGBA no tamanho esperado."""
        img = create_tray_icon_image("#107C41", size=64)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (64, 64))
        self.assertEqual(img.mode, "RGBA")

    def test_system_tray_manager_initialization(self):
        """Testa a inicialização e montagem do menu de contexto dinâmico do tray."""
        tray = SystemTrayManager()
        menu = tray._build_menu()
        self.assertIsNotNone(menu)

    def test_dashboard_status_updates_and_logs(self):
        """Verifica a atualização de status do MCP, extensão e manipulação de logs."""
        dash = self.win.panel_dashboard
        dash.update_mcp_status("Ativo", latency_ms=12.5)
        self.assertIn("Ativo", dash.lbl_mcp_status.cget("text"))
        self.assertIn("12.5 ms", dash.lbl_mcp_latency.cget("text"))

        dash.update_extension_status(True, active_tab="https://example.com")
        self.assertIn("Conectada", dash.lbl_ext_status.cget("text"))

        # Inserção e limpeza de logs
        dash.append_log("Mensagem de teste de diagnóstico")
        self.win.update()
        log_content = dash.txt_logs.get("1.0", "end-1c")
        self.assertIn("Mensagem de teste", log_content)

        dash.clear_logs()
        self.win.update()
        self.assertEqual(dash.txt_logs.get("1.0", "end-1c").strip(), "")

    def test_navigation_and_theme_toggle(self):
        """Valida a alternância de abas entre Dashboard e Configurações e troca de tema."""
        self.win.show_settings()
        self.win.update()
        self.win.show_dashboard()
        self.win.update()

        # Troca de tema
        tema_anterior = self.win._current_theme
        self.win.toggle_theme()
        self.win.update()
        self.assertNotEqual(self.win._current_theme, tema_anterior)
        self.win.toggle_theme()  # Restaura tema original
        self.win.update()

    def test_autostart_query(self):
        """Testa se a checagem de inicialização com o Windows executa sem falhas."""
        resultado = is_autostart_enabled()
        self.assertIsInstance(resultado, bool)


if __name__ == "__main__":
    unittest.main()
