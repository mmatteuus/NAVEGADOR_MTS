"""Regressões do probe local de prontidão do túnel."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json

import pytest

from src.core import tunnel_health


class _Response:
    def __init__(self, status: int, body: bytes = b"{}") -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def _config(tmp_path: Path):
    return SimpleNamespace(app_data_dir=tmp_path, mcp_port=3457)


def _status(tunnel_id: str = "tunnel_" + "a" * 32) -> bytes:
    return (
        '{"control_plane_tunnel_id":"' + tunnel_id + '",'
        '"mcp_server_url":"http://127.0.0.1:3457/mcp",'
        '"channels":[{"name":"main","enabled":true,"server_kind":"external",'
        '"transport_kind":"http-streamable","probe_status":"ok",'
        '"details":[{"key":"address","value":"http://127.0.0.1:3457/mcp"}]}]}'
    ).encode()


def _metrics(timestamp: float) -> bytes:
    return (
        'commands_poll_last_successful_timestamp_seconds{'
        'otel_scope_name="controlplane",otel_scope_schema_url="",'
        'otel_scope_version=""} ' + str(timestamp)
    ).encode()


def test_readyz_and_healthy_status_are_required(tmp_path: Path) -> None:
    """Só há prontidão quando os dois endpoints locais respondem corretamente."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://127.0.0.1:4321\n", encoding="utf-8")
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "urlopen", side_effect=[
            _Response(200), _Response(200, _status()), _Response(200, _metrics(1000.0))
        ]
    ) as mocked, patch.object(tunnel_health, "get_tunnel_id", return_value="tunnel_" + "a" * 32), patch.object(
        tunnel_health.time, "time", return_value=1000.0
    ):
        assert tunnel_health.probe_tunnel_ready()
    assert [call.args[0] for call in mocked.call_args_list] == [
        "http://127.0.0.1:4321/readyz",
        "http://127.0.0.1:4321/api/status",
        "http://127.0.0.1:4321/metrics",
    ]


def test_metadata_auth_error_is_not_ready(tmp_path: Path) -> None:
    """/readyz 200 não encobre erro de metadados 401/invalid_api_key."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://localhost:4321", encoding="utf-8")
    payload = b'{"tunnel_metadata_error":{"status":401,"error":"invalid_api_key"}}'
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "urlopen", side_effect=[_Response(200), _Response(200, payload)]
    ):
        assert not tunnel_health.probe_tunnel_ready()


def test_full_valid_status_with_metadata_error_is_not_ready(tmp_path: Path) -> None:
    """Erro explícito rejeita até um status com identidade e canal válidos."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://127.0.0.1:4321", encoding="utf-8")
    payload = json.loads(_status())
    payload["tunnel_metadata_error"] = {"status": 401, "error": "invalid_api_key"}
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "get_tunnel_id", return_value="tunnel_" + "a" * 32
    ), patch.object(tunnel_health, "urlopen", side_effect=[
        _Response(200), _Response(200, json.dumps(payload).encode())
    ]):
        assert not tunnel_health.probe_tunnel_ready()


def test_identity_channel_or_polling_failure_is_not_ready(tmp_path: Path) -> None:
    """Status sem identidade correta e polling ausente/futuro não passa."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://127.0.0.1:4321", encoding="utf-8")
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "get_tunnel_id", return_value="tunnel_" + "a" * 32
    ), patch.object(tunnel_health, "urlopen", side_effect=[
        _Response(200), _Response(200, _status("tunnel_" + "b" * 32))
    ]):
        assert not tunnel_health.probe_tunnel_ready()
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "get_tunnel_id", return_value="tunnel_" + "a" * 32
    ), patch.object(tunnel_health, "urlopen", side_effect=[
        _Response(200), _Response(200, _status()), _Response(200, _metrics(0.0))
    ]), patch.object(tunnel_health.time, "time", return_value=1000.0):
        assert not tunnel_health.probe_tunnel_ready()


@pytest.mark.parametrize("metrics", [
    b"", b"commands_poll_last_successful_timestamp_seconds NaN",
    _metrics(1000.0 - 91), _metrics(1006.0),
])
def test_missing_malformed_stale_or_future_polling_is_not_ready(tmp_path: Path, metrics: bytes) -> None:
    """Polling ausente, inválido, antigo ou adiantado mantém o estado fechado."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://127.0.0.1:4321", encoding="utf-8")
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "get_tunnel_id", return_value="tunnel_" + "a" * 32
    ), patch.object(tunnel_health, "urlopen", side_effect=[
        _Response(200), _Response(200, _status()), _Response(200, metrics)
    ]), patch.object(tunnel_health.time, "time", return_value=1000.0):
        assert not tunnel_health.probe_tunnel_ready()


def test_status_http_error_or_invalid_json_is_not_ready(tmp_path: Path) -> None:
    """Falha HTTP e payload inválido mantêm o estado fechado."""
    (tmp_path / "tunnel-health-url.txt").write_text("http://127.0.0.1:4321", encoding="utf-8")
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "urlopen", side_effect=[_Response(200), _Response(401)]
    ):
        assert not tunnel_health.probe_tunnel_ready()
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "urlopen", side_effect=[_Response(200), _Response(200, b"invalid")]
    ):
        assert not tunnel_health.probe_tunnel_ready()


def test_non_loopback_health_url_is_rejected(tmp_path: Path) -> None:
    """O probe não consulta hosts, credenciais ou parâmetros externos."""
    (tmp_path / "tunnel-health-url.txt").write_text("https://example.test/status", encoding="utf-8")
    with patch.object(tunnel_health, "current_config", _config(tmp_path)), patch.object(
        tunnel_health, "urlopen"
    ) as mocked:
        assert not tunnel_health.probe_tunnel_ready()
    mocked.assert_not_called()
