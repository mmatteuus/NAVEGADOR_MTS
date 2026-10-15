"""Smoke sem rede do bootstrap Secure MCP Tunnel."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.core.tunnel_service import TunnelService, get_runtime_api_key


def test_tunnel_missing_prerequisites_fail_closed():
    """Sem credenciais, o subprocesso não é iniciado."""
    tunnel = TunnelService()
    with patch("src.core.tunnel_service.find_tunnel_client_binary", return_value=None):
        with patch("src.core.tunnel_service.get_runtime_api_key", return_value=None):
            assert tunnel.start() is False
    assert not tunnel.is_active
    assert "Runtime API Key" in tunnel.last_error


def test_tunnel_process_environment_and_command():
    """Credenciais jamais aparecem nos argumentos nem em arquivos de perfil."""
    created = []

    class FakeSupervisor:
        def __init__(self, **kwargs):
            created.append(kwargs)
            self.alive = True

        def start(self):
            return True

        def is_alive(self):
            return self.alive

        def terminate_tree(self, timeout=1.5):
            self.alive = False

    tunnel = TunnelService()
    with patch("src.core.tunnel_service.find_tunnel_client_binary",
               return_value=Path("C:/Fake/tunnel-client.exe")), \
         patch("src.core.tunnel_service.get_runtime_api_key",
               return_value="sk-test-hidden"), \
         patch("src.core.tunnel_service.local_mcp_is_ready", return_value=True), \
         patch("src.core.tunnel_service.ProcessSupervisor", FakeSupervisor):
        assert tunnel.start()
        try:
            assert created[0]["command"] == ["C:\\Fake\\tunnel-client.exe", "run"]
            assert "sk-test-hidden" not in " ".join(created[0]["command"])
            assert created[0]["env"]["CONTROL_PLANE_API_KEY"] == "sk-test-hidden"
            assert created[0]["env"]["MCP_SERVER_URL"].endswith("/mcp")
        finally:
            tunnel.stop()
    assert not tunnel.is_active


def test_env_key_precedence(monkeypatch):
    """Chave de ambiente tem prioridade sobre o cofre local."""
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "sk-test-from-env")
    assert get_runtime_api_key() == "sk-test-from-env"
