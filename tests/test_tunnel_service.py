"""Smoke sem rede do bootstrap Secure MCP Tunnel."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


def test_tunnel_process_environment_and_command(tmp_path, dynamic_port):
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
    isolated_config = SimpleNamespace(
        app_data_dir=tmp_path, mcp_port=dynamic_port, ensure_directories=lambda: None
    )
    with patch("src.core.tunnel_service.find_tunnel_client_binary",
               return_value=Path("C:/Fake/tunnel-client.exe")), \
         patch("src.core.tunnel_service.get_runtime_api_key",
               return_value="sk-test-hidden"), \
         patch("src.core.tunnel_service.get_tunnel_id",
               return_value="tunnel_" + "a" * 32), \
         patch("src.core.tunnel_service.local_mcp_is_ready", return_value=True), \
         patch("src.core.tunnel_service.probe_tunnel_ready", return_value=False), \
         patch("src.core.tunnel_service.current_config", isolated_config), \
         patch("src.core.tunnel_service.ProcessSupervisor", FakeSupervisor):
        assert tunnel.start()
        try:
            assert created[0]["command"] == [str(Path("C:/Fake/tunnel-client.exe")), "run"]
            assert "sk-test-hidden" not in " ".join(created[0]["command"])
            assert created[0]["env"]["CONTROL_PLANE_API_KEY"] == "sk-test-hidden"
            assert created[0]["env"]["CONTROL_PLANE_TUNNEL_ID"] == "tunnel_" + "a" * 32
            assert created[0]["env"]["MCP_SERVER_URL"].endswith("/mcp")
        finally:
            tunnel.stop()
    assert not tunnel.is_active


def test_tunnel_missing_id_never_starts_supervisor(tmp_path, dynamic_port):
    """Sem Tunnel ID válido, nenhuma tentativa de subprocesso é feita."""
    isolated_config = SimpleNamespace(
        app_data_dir=tmp_path, mcp_port=dynamic_port, ensure_directories=lambda: None
    )
    with patch("src.core.tunnel_service.find_tunnel_client_binary", return_value=Path("C:/Fake/tunnel-client.exe")), \
         patch("src.core.tunnel_service.get_runtime_api_key", return_value="sk-test-hidden"), \
         patch("src.core.tunnel_service.get_tunnel_id", return_value=""), \
         patch("src.core.tunnel_service.ProcessSupervisor") as supervisor:
        with patch("src.core.tunnel_service.current_config", isolated_config):
            tunnel = TunnelService()
            assert tunnel.start() is False
    supervisor.assert_not_called()
    assert "Tunnel ID" in tunnel.last_error


def test_env_key_precedence(monkeypatch):
    """Chave de ambiente tem prioridade sobre o cofre local."""
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "sk-test-from-env")
    assert get_runtime_api_key() == "sk-test-from-env"


def test_tunnel_service_set_status_callback_and_status():
    """Valida o registro do callback de status e a atualização do estado interno."""
    tunnel = TunnelService()
    calls = []

    def status_cb(running: bool, msg: str) -> None:
        calls.append((running, msg))

    # Test sem callback registrado
    tunnel._status(False, "Erro de teste sem callback")
    assert tunnel.last_error == "Erro de teste sem callback"

    tunnel._status(True, "Sucesso de teste sem callback")
    assert tunnel.last_error == ""

    # Registrar callback
    tunnel.set_status_callback(status_cb)

    tunnel._status(False, "Falha na conexão")
    assert tunnel.last_error == "Falha na conexão"
    assert calls == [(False, "Falha na conexão")]

    tunnel._status(True, "Túnel ativo")
    assert tunnel.last_error == ""
    assert calls == [(False, "Falha na conexão"), (True, "Túnel ativo")]
