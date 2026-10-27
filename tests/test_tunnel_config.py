"""Regressões de configuração distribuível e precedência do Tunnel ID."""
from __future__ import annotations

import json
from types import SimpleNamespace

from src.core import config


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


def test_get_tunnel_file_fallback_on_config_error(monkeypatch) -> None:
    """Valida o fallback para APPDATA e home em caso de falha no config."""
    from pathlib import Path
    from src.core.tunnel_config import _get_tunnel_file

    class FaultyConfig:
        @property
        def app_data_dir(self) -> str:
            raise RuntimeError("Erro ao acessar app_data_dir")

    monkeypatch.setattr("src.core.config.current_config", FaultyConfig())

    # Cenário 1: APPDATA definido no ambiente
    monkeypatch.setenv("APPDATA", "/custom/appdata")
    assert _get_tunnel_file() == Path("/custom/appdata/browser-mcp-mts/tunnel.json")

    # Cenário 2: APPDATA não definido nas variáveis de ambiente
    monkeypatch.delenv("APPDATA", raising=False)
    assert _get_tunnel_file() == Path.home() / "browser-mcp-mts" / "tunnel.json"
