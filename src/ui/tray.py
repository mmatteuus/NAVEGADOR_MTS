"""Módulo de Integração com a Bandeja do Sistema (System Tray).

Responsabilidades:
- Exibição de ícone dinâmico com indicador de status no System Tray via pystray.
- Menu de contexto dinâmico com ações rápidas (abrir, alternar trava, sair).
- Threading assíncrono para operação desacoplada do loop do CustomTkinter.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray
from ..computer.safety_gate import safety_gate


def create_tray_icon_image(status_color: str = "#107C41", size: int = 64) -> Image.Image:
    """Gera dinamicamente em memória um ícone moderno para a bandeja do sistema."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill="#202020", outline="#3A3A3A", width=2)

    led_margin = 16
    draw.ellipse([led_margin, led_margin, size - led_margin, size - led_margin], fill=status_color)

    draw.text((size // 2 - 5, size // 2 - 8), "M", fill="#FFFFFF")
    return img


class SystemTrayManager:
    """Gerencia a presença do aplicativo na bandeja do sistema operacional."""

    def __init__(
        self,
        on_show_window: Optional[Callable[[], None]] = None,
        on_toggle_mcp: Optional[Callable[[], None]] = None,
        on_quit_app: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_show_window = on_show_window
        self.on_toggle_mcp = on_toggle_mcp
        self.on_quit_app = on_quit_app
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._status_color: str = "#107C41"

    def _build_menu(self) -> pystray.Menu:
        """Monta o menu de contexto com opções dinâmicas em tempo real."""
        is_auth = safety_gate.is_authorized()
        auth_label = "🛡️ Trava Computer Use: ATIVADA" if is_auth else "🛡️ Trava Computer Use: DESATIVADA"

        def _action_show(icon, item):
            if self.on_show_window:
                self.on_show_window()

        def _action_toggle_safety(icon, item):
            if safety_gate.is_authorized():
                safety_gate.revoke("Ação pelo menu da bandeja")
            else:
                safety_gate.authorize()
            self._refresh_menu()

        def _action_toggle_mcp(icon, item):
            if self.on_toggle_mcp:
                self.on_toggle_mcp()

        def _action_uninstall(icon, item):
            from ..core.uninstaller import trigger_application_uninstall
            self.stop()
            trigger_application_uninstall(self.on_quit_app)

        def _action_exit(icon, item):
            self.stop()
            if self.on_quit_app:
                self.on_quit_app()

        items = [
            pystray.MenuItem("🌐 Abrir NAVEGADOR MTS", _action_show, default=True),
            pystray.MenuItem(auth_label, _action_toggle_safety),
            pystray.MenuItem("🔌 Alternar Servidor MCP", _action_toggle_mcp),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🗑️ Desinstalar Aplicativo", _action_uninstall),
            pystray.MenuItem("❌ Sair do Aplicativo", _action_exit),
        ]
        return pystray.Menu(*items)

    def _refresh_menu(self) -> None:
        """Atualiza os rótulos dinâmicos do menu da bandeja."""
        if self._icon:
            self._icon.menu = self._build_menu()

    def update_status(self, color: str = "#107C41", tooltip: str = "NAVEGADOR MTS Online") -> None:
        """Atualiza a cor do ícone no tray e a dica flutuante de status."""
        self._status_color = color
        if self._icon:
            self._icon.icon = create_tray_icon_image(color)
            self._icon.title = tooltip
            self._refresh_menu()

    def start(self) -> None:
        """Inicia a execução do ícone na bandeja em uma thread secundária."""
        if self._running:
            return
        self._running = True

        def _run_icon():
            self._icon = pystray.Icon(
                name="NavegadorMTS",
                icon=create_tray_icon_image(self._status_color),
                title="NAVEGADOR MTS",
                menu=self._build_menu(),
            )
            self._icon.run()

        self._thread = threading.Thread(target=_run_icon, daemon=True, name="SystemTrayThread")
        self._thread.start()

    def stop(self) -> None:
        """Encerra a exibição do ícone e fecha a thread da bandeja com segurança."""
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
