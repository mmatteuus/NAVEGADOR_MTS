"""Prontidão do Secure MCP Tunnel sem confiar em URLs remotas."""
from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import urlopen
from .config import current_config


def probe_tunnel_ready() -> bool:
    """Consulta apenas o serviço loopback anunciado pelo próprio cliente."""
    path = current_config.app_data_dir / "tunnel-health-url.txt"
    try:
        raw = path.read_text(encoding="utf-8").strip()
        parsed = urlparse(raw)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            return False
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False
        with urlopen(raw.rstrip("/") + "/readyz", timeout=0.4) as response:
            return response.status == 200
    except Exception:
        return False
