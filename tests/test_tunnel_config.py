"""Regressões de configuração distribuível e precedência do Tunnel ID."""
from __future__ import annotations

import json
from types import SimpleNamespace

from src.core import config


import os
from pathlib import Path
from src.core import tunnel_config

def test_get_tunnel_file_fallback_on_exception(monkeypatch) -> None:
    """Verifica fallback para APPDATA/home em caso de falha no config.current_config."""
    monkeypatch.delattr(config, "current_config", raising=False)

    # Test fallback to APPDATA environment variable
    monkeypatch.setenv("APPDATA", "C:\\FakeAppData")
    tunnel_file = tunnel_config._get_tunnel_file()
    assert str(tunnel_file) == str(Path("C:\\FakeAppData") / "browser-mcp-mts" / "tunnel.json")

    # Test fallback to Path.home() when APPDATA is not set
    monkeypatch.delenv("APPDATA", raising=False)
    tunnel_file = tunnel_config._get_tunnel_file()
    assert str(tunnel_file) == str(Path.home() / "browser-mcp-mts" / "tunnel.json")


def test_read_tunnel_data_error_handling(monkeypatch, tmp_path) -> None:
    """Verifica se erros de leitura retornam um dicionário vazio."""
    fake_tunnel_file = tmp_path / "tunnel.json"
    monkeypatch.setattr(tunnel_config, "_get_tunnel_file", lambda: fake_tunnel_file)

    # File doesn't exist
    assert tunnel_config._read_tunnel_data() == {}

    # Invalid JSON
    fake_tunnel_file.write_text("{invalid json", encoding="utf-8")
    assert tunnel_config._read_tunnel_data() == {}

    # OSError simulation
    def mock_read_text(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    assert tunnel_config._read_tunnel_data() == {}


def test_distributed_config_has_no_personal_tunnel_id(monkeypatch) -> None:
    """O padrão do pacote não contém identificador pessoal embutido."""
    monkeypatch.delenv("BROWSER_MTS_TUNNEL_ID", raising=False)
    assert config.load_config().tunnel_id == ""


def test_tunnel_id_precedence_env_then_local_then_empty(monkeypatch, tmp_path) -> None:
    """Ambiente vence o arquivo; sem ambos o padrão permanece vazio."""
    local = "tunnel_" + "a" * 32
    env_id = "tunnel_" + "b" * 32
    fake = SimpleNamespace(app_data_dir=tmp_path, tunnel_id="")
    monkeypatch.setattr(config, "current_config", fake)
    monkeypatch.delenv("BROWSER_MTS_TUNNEL_ID", raising=False)
    assert config.get_tunnel_id() == ""
    (tmp_path / "tunnel.json").write_text(json.dumps({"tunnel_id": local}), encoding="utf-8")
    assert config.get_tunnel_id() == local
    monkeypatch.setenv("BROWSER_MTS_TUNNEL_ID", env_id)
    assert config.get_tunnel_id() == env_id
