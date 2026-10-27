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


def test_read_tunnel_data_handles_corrupted_json_and_os_error(monkeypatch, tmp_path) -> None:
    """Trata erros de JSON malformatado e erro de E/S retornando dicionário vazio."""
    from src.core.tunnel_config import _read_tunnel_data
    fake = SimpleNamespace(app_data_dir=tmp_path)
    monkeypatch.setattr(config, "current_config", fake)

    tunnel_file = tmp_path / "tunnel.json"
    tunnel_file.write_text("{invalid_json: ", encoding="utf-8")
    assert _read_tunnel_data() == {}

    def mock_read_text(*args, **kwargs):
        raise OSError("Falha na leitura do disco")

    monkeypatch.setattr("pathlib.Path.read_text", mock_read_text)
    assert _read_tunnel_data() == {}
