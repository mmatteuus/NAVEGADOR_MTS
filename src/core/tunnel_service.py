"""Supervisão isolada do Secure MCP Tunnel para o MCP HTTP local."""
import json, os, shutil, sys, threading
from pathlib import Path
from typing import Callable, List, Optional
from urllib.request import urlopen
from .config import current_config, get_tunnel_id
from .security import decrypt_dpapi
from .credential_validation import is_runtime_credential
from .tunnel_health import get_health_file_path, probe_tunnel_ready
from .supervisor import ProcessSupervisor

TUNNEL_ID = current_config.tunnel_id


def find_tunnel_client_binary() -> Optional[Path]:
    """Procura binário sem depender de caminhos pessoais de outra máquina."""
    roots = [Path(sys.executable).resolve().parent, current_config.project_root]
    candidates = [root / "tunnel-client.exe" for root in roots]
    candidates.append(current_config.project_root / "BROWSER-MCP-MTS-PORTATIL" / "tunnel-client.exe")
    if prog := shutil.which("tunnel-client"):
        candidates.append(Path(prog))
    return next((path for path in candidates if path.is_file()), None)

def get_tunnel_config_path() -> Optional[Path]:
    """Compatibilidade para diagnóstico de perfis anteriores (não utilizados)."""
    path = current_config.app_data_dir / "browser-mts-runtime.yaml"
    return path if path.is_file() else None

def get_runtime_api_key() -> Optional[str]:
    """Obtém credencial somente do ambiente ou do cofre DPAPI do Windows."""
    key = os.environ.get("CONTROL_PLANE_API_KEY", "").strip()
    if is_runtime_credential(key):
        return key
    try:
        file = current_config.credentials_file
        stored = decrypt_dpapi(file.read_text(encoding="utf-8").strip()) if file.is_file() else None
        return stored if is_runtime_credential(stored) else None
    except Exception:
        return None

def local_mcp_is_ready() -> bool:
    """Confirma que a porta HTTP pertence à instância correta do aplicativo."""
    try:
        with urlopen(f"http://127.0.0.1:{current_config.mcp_port}/healthz", timeout=0.5) as r:
            return r.status == 200 and json.loads(r.read()).get("service") == "browser-mcp-mts"
    except Exception:
        return False

class TunnelService:
    """Reinicia falhas com backoff e suporta perfis isolados sem colisão de health_file."""

    def __init__(self, profile_id: Optional[str] = None, tunnel_id: Optional[str] = None,
                 health_file: Optional[Path] = None, provider: str = "openai",
                 custom_command: Optional[List[str]] = None) -> None:
        self.profile_id, self._tunnel_id = profile_id, tunnel_id
        self._health_file = Path(health_file) if health_file is not None else None
        self.provider = (provider or "openai").strip().lower()
        self.custom_command = list(custom_command) if custom_command else None
        self._supervisor: Optional[ProcessSupervisor] = None
        self._stop, self._monitor_thread = threading.Event(), None
        self._on_status_change: Optional[Callable[[bool, str], None]] = None
        self.last_error, self._ready = "", False

    @property
    def health_file_path(self) -> Path:
        return get_health_file_path(self.profile_id, self._health_file)
    @property
    def is_active(self) -> bool:
        return bool(self._supervisor and self._supervisor.is_alive())
    @property
    def is_ready(self) -> bool:
        return self.is_active and self._ready
    def set_status_callback(self, cb: Callable[[bool, str], None]) -> None:
        self._on_status_change = cb
    def _status(self, running: bool, message: str) -> None:
        self.last_error = "" if running else message
        if self._on_status_change:
            self._on_status_change(running, message)

    def start(self) -> bool:
        if self.is_active:
            return True
        if self.provider in ("cloudflared", "custom") and self.custom_command:
            if not local_mcp_is_ready():
                self._status(False, "Servidor MCP HTTP local indisponível.")
                return False
            sup = ProcessSupervisor(command=self.custom_command, env=os.environ.copy(), name=f"tunnel_{self.profile_id or self.provider}", restart_delay=2.0)
            if not sup.start():
                self._status(False, f"Falha ao executar túnel {self.provider}.")
                return False
            self._supervisor, self._ready, self._stop = sup, True, threading.Event()
            self._status(True, f"Túnel {self.provider} iniciado.")
            return True
        binary, key, tid = find_tunnel_client_binary(), get_runtime_api_key(), (self._tunnel_id or get_tunnel_id())
        if not binary or not key or not tid:
            self._status(False, "Configure tunnel-client.exe, Runtime API Key e Tunnel ID.")
            return False
        if not local_mcp_is_ready():
            self._status(False, "Servidor MCP HTTP local indisponível.")
            return False
        current_config.ensure_directories()
        hfile = self.health_file_path
        hfile.unlink(missing_ok=True)
        env = {**os.environ, "HEALTH_LISTEN_ADDR": "127.0.0.1:0", "HEALTH_URL_FILE": str(hfile),
               "CONTROL_PLANE_API_KEY": key, "CONTROL_PLANE_TUNNEL_ID": tid, "MCP_SERVER_URL": f"http://127.0.0.1:{current_config.mcp_port}/mcp"}
        sup = ProcessSupervisor(command=[str(binary), "run"], env=env, name="secure_mcp_tunnel", restart_delay=2.0)
        if not sup.start():
            self._status(False, "Falha ao executar tunnel-client.exe.")
            return False
        self._supervisor, self._ready, self._stop = sup, False, threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor, args=(self._stop,), daemon=True, name="TunnelMonitor")
        self._monitor_thread.start()
        self._status(True, "Processo do túnel iniciado; conexão remota não verificada.")
        return True

    def _monitor(self, stop: threading.Event) -> None:
        attempts = 0
        while not stop.wait(2.0):
            if not (sup := self._supervisor):
                return
            if sup.is_alive():
                is_def = self.profile_id is None and self._health_file is None and self._tunnel_id is None
                self._ready = probe_tunnel_ready() if is_def else probe_tunnel_ready(self.profile_id, self.health_file_path, self._tunnel_id or get_tunnel_id())
                attempts = 0
                continue
            self._ready = False
            self._status(False, "Túnel encerrou; verificando recuperação.")
            if stop.wait(min(30, 2 ** min(attempts + 1, 5))):
                break
            if not stop.is_set() and local_mcp_is_ready() and sup.restart():
                attempts = 0
                self._status(True, "Túnel reiniciado; confirme /readyz do cliente.")
            else:
                attempts += 1

    def stop(self) -> None:
        self._stop.set()
        self._ready = False
        if sup := self._supervisor:
            self._supervisor = None
            sup.terminate_tree(timeout=1.5)
        self._status(False, "Túnel desligado pelo aplicativo.")

tunnel_service = TunnelService()
