"""Módulo de Configuração Centralizada do BROWSER MTS.

Responsabilidades:
- Centralização de portas de rede (porta de desenvolvimento 3456, host local).
- Definição padronizada de caminhos de arquivos, segredos, logs e executáveis.
- Leitura de variáveis de ambiente com fallback para padrões seguros de produção.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import sys

from .tunnel_config import (
    get_tunnel_id,
    save_tunnel_id,
    get_tunnel_name,
    save_tunnel_name,
    get_tunnel_display_label,
)

__all__ = [
    "AppConfig",
    "load_config",
    "current_config",
    "get_tunnel_id",
    "save_tunnel_id",
    "get_tunnel_name",
    "save_tunnel_name",
    "get_tunnel_display_label",
    "DEFAULT_HOST",
    "DEFAULT_DEV_PORT",
    "DEFAULT_MCP_PORT",
]

# Definições padronizadas de rede
DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_DEV_PORT: int = 3456
DEFAULT_MCP_PORT: int = 3457
DEFAULT_TUNNEL_ID: str = ""


def _get_project_root() -> Path:
    """Retorna o diretório raiz seja executando em código fonte ou .exe congelado."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    return Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class AppConfig:
    """Configurações imutáveis do aplicativo BROWSER MTS."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_DEV_PORT
    mcp_port: int = DEFAULT_MCP_PORT
    tunnel_id: str = DEFAULT_TUNNEL_ID
    dev_mode: bool = False

    # Diretórios e caminhos absolutos
    project_root: Path = field(default_factory=_get_project_root)
    app_data_dir: Path = field(default_factory=lambda: Path(
        os.environ.get("APPDATA", str(Path.home()))
    ) / "browser-mcp-mts")

    @property
    def secrets_dir(self) -> Path:
        """Diretório isolado para armazenamento seguro de credenciais."""
        return self.app_data_dir / "secrets"

    @property
    def credentials_file(self) -> Path:
        """Arquivo criptografado com a Runtime API Key via DPAPI."""
        return self.secrets_dir / "runtime_key.enc"

    @property
    def logs_dir(self) -> Path:
        """Diretório para armazenamento de arquivos de log do aplicativo."""
        return self.app_data_dir / "logs"

    @property
    def log_file(self) -> Path:
        """Caminho completo para o arquivo principal de log."""
        return self.logs_dir / "browser_mts.log"

    @property
    def tunnel_bin_path(self) -> Path:
        """Localização do executável do túnel seguro OpenAI."""
        local_bin = self.project_root / "bin" / "tunnel-client.exe"
        if local_bin.exists():
            return local_bin
        portable_bin = self.project_root / "BROWSER-MCP-MTS-PORTATIL" / "tunnel-client.exe"
        return portable_bin

    def ensure_directories(self) -> None:
        """Cria os diretórios essenciais de dados, logs e segredos se não existirem."""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """Carrega as configurações a partir do ambiente ou padrões do sistema."""
    host = os.environ.get("BROWSER_MTS_HOST", DEFAULT_HOST)
    port_str = os.environ.get("BROWSER_MTS_PORT", str(DEFAULT_DEV_PORT))
    mcp_port_str = os.environ.get("BROWSER_MTS_MCP_PORT", str(DEFAULT_MCP_PORT))
    tunnel_id = os.environ.get("BROWSER_MTS_TUNNEL_ID", DEFAULT_TUNNEL_ID)
    dev_mode = os.environ.get("BROWSER_MTS_DEV_MODE", "0").lower() in ("1", "true", "yes")

    try:
        port = int(port_str)
    except ValueError:
        port = DEFAULT_DEV_PORT

    try:
        mcp_port = int(mcp_port_str)
    except ValueError:
        mcp_port = DEFAULT_MCP_PORT

    return AppConfig(
        host=host,
        port=port,
        mcp_port=mcp_port,
        tunnel_id=tunnel_id,
        dev_mode=dev_mode,
    )


# Instância global pré-carregada para uso nos módulos
current_config: AppConfig = load_config()
