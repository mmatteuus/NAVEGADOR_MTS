"""Prontidão do Secure MCP Tunnel sem confiar em URLs remotas."""
from __future__ import annotations

import json
import math
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


def _status_is_healthy(payload: object, expected_id: str, mcp_url: str) -> bool:
    """Aceita somente a identidade e o canal MCP observados no status."""
    if not isinstance(payload, dict) or payload.get("tunnel_metadata_error"):
        return False
    if payload.get("control_plane_tunnel_id") != expected_id:
        return False
    if payload.get("mcp_server_url") != mcp_url:
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
        base_url = raw.rstrip("/")
        with urlopen(base_url + "/readyz", timeout=0.4) as response:
            if response.status != 200:
                return False
        with urlopen(base_url + "/api/status", timeout=0.4) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read())
        expected_id = get_tunnel_id()
        mcp_url = f"http://127.0.0.1:{current_config.mcp_port}/mcp"
        if not expected_id or not _status_is_healthy(payload, expected_id, mcp_url):
            return False
        with urlopen(base_url + "/metrics", timeout=0.4) as response:
            if response.status != 200:
                return False
            metrics = response.read()
        return _polling_is_recent(metrics, time.time())
    except Exception:
        return False
