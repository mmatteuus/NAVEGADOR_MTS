"""Pacote de Interface Gráfica Windows 11 Fluent Design do BROWSER MTS.

Módulos exportados:
- main_window: Janela principal com efeito Mica e abas Fluent.
- theme: Paleta de cores, tipografia e estilização do sistema operacional.
- tray: Integração com a bandeja do sistema (System Tray) via pystray.
- notifications: Notificações Toast nativas com debouncing.
- dashboard_panel: Painel de métricas e status em tempo real.
- settings_panel: Painel de configurações com proteção de segredos DPAPI.
"""

from .dashboard_panel import DashboardPanel
from .main_window import MainWindow
from .notifications import ToastNotifier, notifier
from .settings_panel import SettingsPanel
from .theme import PALETTE, apply_mica_theme, configure_app_theme, get_status_color
from .tray import SystemTrayManager, create_tray_icon_image

__all__ = [
    "MainWindow",
    "DashboardPanel",
    "SettingsPanel",
    "SystemTrayManager",
    "ToastNotifier",
    "notifier",
    "PALETTE",
    "apply_mica_theme",
    "configure_app_theme",
    "get_status_color",
    "create_tray_icon_image",
]
