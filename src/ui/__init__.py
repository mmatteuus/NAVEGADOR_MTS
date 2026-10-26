"""Pacote de Interface Gráfica Moderna Dual-Mode para Windows do NAVEGADOR MTS.

Módulos exportados:
- main_window: Janela principal com suporte Dual-Mode (Claro e Escuro) e abas modernas.
- theme: Paleta de cores WCAG AAA, tipografia universal e estilização DWM.
- tray: Integração com a bandeja do sistema (System Tray) via pystray.
- notifications: Notificações Toast nativas com debouncing.
- dashboard_panel: Painel de métricas e status em tempo real.
- ai_connections_panel: Painel de conexão Multi-IA e perfis Multi-Túneis.
- settings_panel: Painel de configurações com proteção de segredos DPAPI.
"""

from .ai_connections_panel import AIConnectionsPanel
from .dashboard_panel import DashboardPanel
from .main_window import MainWindow
from .notifications import ToastNotifier, notifier
from .settings_panel import SettingsPanel
from .theme import PALETTE, apply_mica_theme, configure_app_theme, get_status_color
from .tray import SystemTrayManager, create_tray_icon_image
from .update_dialog import UpdateDialog
from .mcp_copy_dialog import MCPConnectDialog, show_mcp_dialog

__all__ = [
    "MainWindow",
    "DashboardPanel",
    "AIConnectionsPanel",
    "SettingsPanel",
    "SystemTrayManager",
    "ToastNotifier",
    "notifier",
    "PALETTE",
    "apply_mica_theme",
    "configure_app_theme",
    "get_status_color",
    "create_tray_icon_image",
    "UpdateDialog",
    "MCPConnectDialog",
    "show_mcp_dialog",
]
