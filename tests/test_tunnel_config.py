"""Regressões de configuração distribuível e precedência do Tunnel ID."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.core import config
from src.core.tunnel_config import _read_tunnel_data


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


def test_read_tunnel_data_invalid_json(monkeypatch, tmp_path) -> None:
    """Testa se leitura de arquivo JSON inválido (ValueError) retorna dicionário vazio."""
    fake = SimpleNamespace(app_data_dir=tmp_path, tunnel_id="")
    monkeypatch.setattr(config, "current_config", fake)

    file_path = tmp_path / "tunnel.json"
    file_path.write_text("isto não é json", encoding="utf-8")

    assert _read_tunnel_data() == {}


def test_read_tunnel_data_oserror(monkeypatch, tmp_path) -> None:
    """Testa se OSError na leitura do arquivo retorna dicionário vazio."""
    fake = SimpleNamespace(app_data_dir=tmp_path, tunnel_id="")
    monkeypatch.setattr(config, "current_config", fake)

    file_path = tmp_path / "tunnel.json"
    file_path.write_text('{"tunnel_id": "test"}', encoding="utf-8")

    def mock_read_text(*args, **kwargs):
        raise OSError("Erro simulado")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    assert _read_tunnel_data() == {}
