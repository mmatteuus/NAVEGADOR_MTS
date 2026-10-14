"""Serviço de Gerenciamento do Túnel OpenAI (ChatGPT) no BROWSER MTS.

Responsabilidades:
- Inicialização e supervisão contínua do tunnel-client.exe com auto-recuperação.
- Manutenção da conexão ativa em background sem depender de janelas de terminal.
- Integração thread-safe com o ciclo de vida do aplicativo desktop e callbacks da UI.
"""

from __future__ import annotations
import os
from pathlib import Path
import threading
import time
from typing import Callable, Optional
from .config import current_config
from .supervisor import ProcessSupervisor

TUNNEL_ID: str = "tunnel_6a7aea545c408191889cd114d4a99d9b"


def find_tunnel_client_binary() -> Optional[Path]:
    """Localiza o binário oficial do tunnel-client no sistema."""
    candidates = [
        current_config.tunnel_bin_path,
        Path(r"C:\Users\MATEUS\browser mcp mts\BROWSER-MCP-MTS-PORTATIL\tunnel-client.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "BROWSER MTS" / "tunnel-client.exe",
        current_config.project_root / "tunnel-client.exe",
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


def get_tunnel_config_path() -> Optional[Path]:
    """Retorna o caminho do arquivo de perfil YAML do túnel."""
    candidates = [
        Path(r"C:\Users\MATEUS\browser mcp mts\BROWSER-MCP-MTS-PORTATIL\config\profiles\browser-mts-runtime.yaml"),
        current_config.project_root / "BROWSER-MCP-MTS-PORTATIL" / "config" / "profiles" / "browser-mts-runtime.yaml",
        current_config.app_data_dir / "browser-mts-runtime.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


class TunnelService:
    """Gerenciador do túnel OpenAI que mantém a conexão sempre viva para o ChatGPT."""

    def __init__(self) -> None:
        self._supervisor: Optional[ProcessSupervisor] = None
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._on_status_change: Optional[Callable[[bool, str], None]] = None

    @property
    def is_active(self) -> bool:
        """Verifica se o processo do túnel está ativo e operacional."""
        return self._supervisor is not None and self._supervisor.is_alive()

    def set_status_callback(self, cb: Callable[[bool, str], None]) -> None:
        """Define callback invocado quando o estado do túnel altera."""
        self._on_status_change = cb

    def start(self) -> bool:
        """Inicia o tunnel-client em segundo plano com supervisão ativa."""
        if self.is_active:
            return True

        bin_path = find_tunnel_client_binary()
        cfg_path = get_tunnel_config_path()

        if not bin_path or not cfg_path:
            if self._on_status_change:
                self._on_status_change(False, "Binário ou perfil de túnel não encontrado")
            return False

        cmd = [str(bin_path), "run", "--config", str(cfg_path)]
        self._supervisor = ProcessSupervisor(command=cmd, name="openai_tunnel_supervisor", restart_delay=1.0)
        started = self._supervisor.start()
        self._running = started

        if started:
            self._start_monitor_loop()
            if self._on_status_change:
                self._on_status_change(True, f"Conectado ({TUNNEL_ID})")
        return started

    def _start_monitor_loop(self) -> None:
        """Monitora continuamente o túnel e restabelece a conexão se cair."""
        def _loop():
            while self._running:
                time.sleep(2.0)
                if self._running and self._supervisor and not self._supervisor.is_alive():
                    # Auto-cura imediata em caso de oscilação de rede
                    self._supervisor.restart(reason="Auto-recuperação do túnel")
                    if self._on_status_change:
                        self._on_status_change(self.is_active, "Reconectado após oscilação")

        self._monitor_thread = threading.Thread(target=_loop, daemon=True, name="TunnelMonitorThread")
        self._monitor_thread.start()

    def stop(self) -> None:
        """Finaliza graciosamente o túnel e seus processos filhos."""
        self._running = False
        if self._supervisor:
            self._supervisor.terminate_tree(timeout=1.5)
            self._supervisor = None
        if self._on_status_change:
            self._on_status_change(False, "Desconectado pelo aplicativo")


# Instância global singleton do serviço de túnel
tunnel_service: TunnelService = TunnelService()

