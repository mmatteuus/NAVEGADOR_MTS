"""Ponto de Entrada Principal da Aplicação Desktop BROWSER MTS.

Responsabilidades:
- Inicialização unificada dos serviços de segundo plano (WebSocket Bridge, Kill-Switch).
- Orquestração da Interface Gráfica Windows 11 Fluent e do System Tray.
- Suporte a inicialização silenciosa na bandeja (--minimized) e encerramento limpo.
"""

import argparse
import asyncio
import threading
from typing import Optional
from .core.config import current_config
from .core.tunnel_service import tunnel_service
from .computer.kill_switch import kill_switch
from .mcp.ws_bridge import WebSocketBridge
from .mcp.server import MCPServer
from .mcp.http_server import MCPHTTPServer
from .ui import MainWindow, SystemTrayManager, configure_app_theme, notifier


class DesktopApplication:
    """Coordenador do ciclo de vida da aplicação Desktop."""

    def __init__(self, start_minimized: bool = False) -> None:
        self.start_minimized = start_minimized
        self.ws_bridge = WebSocketBridge(host=current_config.host, port=current_config.port)
        self.http_mcp = MCPHTTPServer(MCPServer(ws_bridge=self.ws_bridge), current_config.mcp_port)
        self.http_error: Optional[str] = None
        self.ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.window: Optional[MainWindow] = None
        self.tray: Optional[SystemTrayManager] = None
        self._running = False

    def _start_background_services(self) -> None:
        """Sobe o servidor WebSocket local e o hook de emergência em threads dedicadas."""
        self.ws_loop = asyncio.new_event_loop()

        def _run_ws():
            asyncio.set_event_loop(self.ws_loop)
            self.ws_loop.run_until_complete(self.ws_bridge.start())
            try:
                self.ws_loop.run_until_complete(self.http_mcp.start())
                threading.Thread(target=tunnel_service.start, daemon=True,
                                 name="TunnelStarter").start()
            except OSError as exc:
                self.http_error = str(exc)
            self.ws_loop.run_forever()

        self.ws_thread = threading.Thread(target=_run_ws, daemon=True, name="WSBridgeThread")
        self.ws_thread.start()

        # Inicia a escuta global do Kill-Switch e o Túnel persistente OpenAI
        kill_switch.start()

    def _poll_status_cycle(self) -> None:
        """Ciclo periódico (1s) para sincronização de métricas e status com a UI."""
        if not self._running or not self.window:
            return

        is_ext = self.ws_bridge.is_connected
        lat = self.ws_bridge.last_latency_ms
        active_tab = self.ws_bridge.client_info.get("activeTabUrl", "")
        self.window.panel_dashboard.update_mcp_status("Ativo", latency_ms=lat, port=self.ws_bridge.port)
        self.window.panel_dashboard.update_extension_status(is_ext, active_tab=active_tab)
        tun_status = ("Pronto (/readyz)" if tunnel_service.is_ready
            else "Processo iniciado, aguardando prontidão" if tunnel_service.is_active
            else self.http_error or tunnel_service.last_error or "Desconectado")
        self.window.panel_dashboard.lbl_mcp_tunnel.configure(text=f"Túnel ChatGPT: {tun_status}")

        # Atualiza a cor e o tooltip no System Tray
        if is_ext:
            self.tray.update_status("#107C41", f"Navegador MTS (Porta {self.ws_bridge.port}): Conectado e Operacional")
        else:
            self.tray.update_status("#D83B01", f"Navegador MTS (Porta {self.ws_bridge.port}): Aguardando Extensão")

        self.window.after(1000, self._poll_status_cycle)

    def shutdown(self) -> None:
        """Encerra graciosamente todos os serviços, threads e janelas."""
        self._running = False
        kill_switch.stop()
        tunnel_service.stop()
        if self.tray:
            self.tray.stop()
        if self.ws_loop and self.ws_loop.is_running():
            async def _close():
                await self.http_mcp.stop()
                await self.ws_bridge.stop()
            try:
                asyncio.run_coroutine_threadsafe(_close(), self.ws_loop).result(timeout=5)
            except Exception:
                pass
            self.ws_loop.call_soon_threadsafe(self.ws_loop.stop())
        if self.window:
            self.window.destroy()

    def run(self) -> None:
        """Inicializa a interface visual e entra no loop de eventos principal."""
        self._running = True
        configure_app_theme("dark")
        self._start_background_services()

        self.window = MainWindow(
            on_close_to_tray=lambda: notifier.notify(
                "Navegador MTS em Segundo Plano",
                "O processamento continua ativo! O 'X' apenas fecha a janela. Para encerrar de verdade, use a bandeja."
            ),
            on_quit_app=self.shutdown,
        )

        self.tray = SystemTrayManager(
            on_show_window=self.window.show_from_tray,
            on_toggle_mcp=lambda: self.window.panel_dashboard.append_log("Toggle MCP solicitado."),
            on_quit_app=self.shutdown,
        )
        self.tray.start()

        if self.start_minimized:
            self.window.withdraw()

        self.window.after(500, self._poll_status_cycle)
        # Verificação automática em segundo plano de novas versões 5s após startup
        self.window.after(5000, lambda: self.window.check_for_updates_ui(auto_open=True))
        self.window.mainloop()


def main() -> None:
    """Função principal de entrada CLI do aplicativo."""
    parser = argparse.ArgumentParser(description="Navegador MTS - Aplicativo Desktop Windows 11")
    parser.add_argument("--minimized", action="store_true", help="Iniciar silenciosamente na bandeja")
    parser.add_argument("--stdio", action="store_true", help="Modo Servidor MCP Stdio para ChatGPT, Claude e túneis")
    args = parser.parse_args()

    if args.stdio:
        from .mcp.server import MCPServer
        srv = MCPServer(host=current_config.host, ws_port=current_config.port)

        async def _run_mcp():
            await srv.start(start_ws=True)
            await srv.run_stdio()

        try:
            asyncio.run(_run_mcp())
        except KeyboardInterrupt:
            pass
        return

    app = DesktopApplication(start_minimized=args.minimized)
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == "__main__":
    main()
