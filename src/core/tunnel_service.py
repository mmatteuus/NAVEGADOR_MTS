"""Supervisão isolada do Secure MCP Tunnel para o MCP HTTP local."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import threading
from typing import Callable, Optional
from urllib.request import urlopen

from .config import current_config
from .security import decrypt_dpapi
from .supervisor import ProcessSupervisor

TUNNEL_ID = current_config.tunnel_id


def find_tunnel_client_binary() -> Optional[Path]:
    """Procura binário sem depender de caminhos pessoais de outra máquina."""
    roots = [Path(sys.executable).resolve().parent, current_config.project_root]
    candidates = [root / "tunnel-client.exe" for root in roots]
    candidates.append(current_config.project_root / "BROWSER-MCP-MTS-PORTATIL" / "tunnel-client.exe")
    program = shutil.which("tunnel-client")
    if program:
        candidates.append(Path(program))
    return next((path for path in candidates if path.is_file()), None)


def get_tunnel_config_path() -> Optional[Path]:
    """Compatibilidade para diagnóstico de perfis anteriores (não utilizados)."""
    path = current_config.app_data_dir / "browser-mts-runtime.yaml"
    return path if path.is_file() else None


def get_runtime_api_key() -> Optional[str]:
    """Obtém credencial somente do ambiente ou do cofre DPAPI do Windows."""
    key = os.environ.get("CONTROL_PLANE_API_KEY", "").strip()
    if key:
        return key
    try:
        file = current_config.credentials_file
        return decrypt_dpapi(file.read_text(encoding="utf-8").strip()) if file.is_file() else None
    except Exception:
        return None


def local_mcp_is_ready() -> bool:
    """Confirma que a porta HTTP pertence à instância correta do aplicativo."""
    try:
        with urlopen(f"http://127.0.0.1:{current_config.mcp_port}/healthz", timeout=0.5) as r:
            import json
            data = json.loads(r.read())
            return r.status == 200 and data.get("service") == "browser-mcp-mts"
    except Exception:
        return False


class TunnelService:
    """Reinicia falhas com backoff e não confunde PID vivo com conexão pronta."""

    def __init__(self) -> None:
        self._supervisor: Optional[ProcessSupervisor] = None
        self._stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._on_status_change: Optional[Callable[[bool, str], None]] = None
        self.last_error = ""

    @property
    def is_active(self) -> bool:
        return bool(self._supervisor and self._supervisor.is_alive())

    def set_status_callback(self, cb: Callable[[bool, str], None]) -> None:
        self._on_status_change = cb

    def _status(self, running: bool, message: str) -> None:
        self.last_error = "" if running else message
        if self._on_status_change:
            self._on_status_change(running, message)

    def start(self) -> bool:
        if self.is_active:
            return True
        binary = find_tunnel_client_binary()
        key = get_runtime_api_key()
        if not binary or not key:
            self._status(False, "Configure tunnel-client.exe e Runtime API Key.")
            return False
        if not local_mcp_is_ready():
            self._status(False, "Servidor MCP HTTP local indisponível.")
            return False
        env = os.environ.copy()
        env["CONTROL_PLANE_API_KEY"] = key
        env["CONTROL_PLANE_TUNNEL_ID"] = current_config.tunnel_id
        env["MCP_SERVER_URL"] = f"http://127.0.0.1:{current_config.mcp_port}/mcp"
        supervisor = ProcessSupervisor(command=[str(binary), "run"], env=env,
                                       name="secure_mcp_tunnel", restart_delay=2.0)
        if not supervisor.start():
            self._status(False, "Falha ao executar tunnel-client.exe.")
            return False
        self._supervisor = supervisor
        self._stop = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor, args=(self._stop,),
                                                daemon=True, name="TunnelMonitor")
        self._monitor_thread.start()
        self._status(True, "Processo do túnel iniciado; conexão remota não verificada.")
        return True

    def _monitor(self, stop: threading.Event) -> None:
        attempts = 0
        while not stop.wait(2.0):
            supervisor = self._supervisor
            if not supervisor or supervisor.is_alive():
                attempts = 0
                continue
            self._status(False, "Túnel encerrou; verificando recuperação.")
            if stop.wait(min(30, 2 ** min(attempts + 1, 5))):
                break
            if not stop.is_set() and local_mcp_is_ready() and supervisor.restart():
                attempts = 0
                self._status(True, "Túnel reiniciado; confirme /readyz do cliente.")
            else:
                attempts += 1

    def stop(self) -> None:
        self._stop.set()
        supervisor, self._supervisor = self._supervisor, None
        if supervisor:
            supervisor.terminate_tree(timeout=1.5)
        self._status(False, "Túnel desligado pelo aplicativo.")


tunnel_service = TunnelService()
