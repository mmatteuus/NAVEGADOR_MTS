"""Prontidão do Secure MCP Tunnel sem confiar em URLs remotas."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import urlopen
from .config import current_config, get_tunnel_id

_POLL_METRIC = re.compile(
    r"^commands_poll_last_successful_timestamp_seconds\{(?P<labels>[^}]*)\}\s+(?P<value>\S+)\s*$"
)
_REQUIRED_LABELS = (
    'otel_scope_name="controlplane"',
    'otel_scope_schema_url=""',
    'otel_scope_version=""',
)


def get_health_file_path(
    profile_id: str | None = None, health_file: Path | str | None = None
) -> Path:
    """Resolve o arquivo de saúde isolado por perfil para evitar colisão com o túnel principal."""
    if health_file is not None:
        return Path(health_file)
    if not profile_id or profile_id in ("primary", "default"):
        return current_config.app_data_dir / "tunnel-health-url.txt"
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(profile_id).strip())
    return current_config.app_data_dir / f"tunnel-health-url-{safe_id}.txt"


def _status_is_healthy(payload: object, expected_id: str, mcp_url: str) -> bool:
    """Aceita somente a identidade e o canal MCP observados no status."""
    if not isinstance(payload, dict) or payload.get("tunnel_metadata_error"):
        return False
    if payload.get("control_plane_tunnel_id") != expected_id or payload.get("mcp_server_url") != mcp_url:
        return False
    channels = payload.get("channels")
    channel = next((item for item in channels or [] if isinstance(item, dict) and item.get("name") == "main"), None)
    if not isinstance(channel, dict) or not all(
        channel.get(key) == value for key, value in (
            ("enabled", True), ("server_kind", "external"),
            ("transport_kind", "http-streamable"), ("probe_status", "ok"),
        )
    ):
        return False
    details = channel.get("details")
    return isinstance(details, list) and any(
        item.get("key") == "address" and item.get("value") == mcp_url
        for item in details if isinstance(item, dict)
    )


def _polling_is_recent(body: bytes, now: float) -> bool:
    """Exige timestamp positivo, finito e recente do polling de comandos."""
    for line in body.decode("utf-8").splitlines():
        match = _POLL_METRIC.match(line.strip())
        if not match or not all(label in match.group("labels") for label in _REQUIRED_LABELS):
            continue
        try:
            timestamp = float(match.group("value"))
        except ValueError:
            continue
        if math.isfinite(timestamp) and 0 < timestamp <= now + 5 and now - timestamp <= 90:
            return True
    return False


def probe_tunnel_ready(
    profile_id: str | None = None,
    health_file: Path | str | None = None,
    expected_id: str | None = None,
) -> bool:
    """Consulta apenas o serviço loopback anunciado pelo próprio cliente."""
    path = get_health_file_path(profile_id=profile_id, health_file=health_file)
    try:
        raw = path.read_text(encoding="utf-8").strip()
        parsed = urlparse(raw)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            return False
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False
        base_url = raw.rstrip("/")
        with urlopen(base_url + "/readyz", timeout=0.4) as response:
            if response.status != 200:
                return False
        with urlopen(base_url + "/api/status", timeout=0.4) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read())
        target_id = expected_id if expected_id is not None else get_tunnel_id()
        mcp_url = f"http://127.0.0.1:{current_config.mcp_port}/mcp"
        if not target_id or not _status_is_healthy(payload, target_id, mcp_url):
            return False
        with urlopen(base_url + "/metrics", timeout=0.4) as response:
            return response.status == 200 and _polling_is_recent(response.read(), time.time())
    except Exception:
        return False
