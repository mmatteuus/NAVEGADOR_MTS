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

def test_tunnel_id_config_exception(monkeypatch) -> None:
    """Verifica se get_tunnel_id lida corretamente com exceções ao acessar tunnel_id da configuração atual."""
    class BuggyConfig:
        @property
        def tunnel_id(self):
            raise Exception("Mock error accessing tunnel_id")

    monkeypatch.delenv("BROWSER_MTS_TUNNEL_ID", raising=False)
    # Ignora o arquivo de túnel gravado (ou mocka get_tunnel_data se preferir)
    monkeypatch.setattr(config, "current_config", BuggyConfig())
    # O arquivo pode existir, então vamos apagar ou mockar _read_tunnel_data
    monkeypatch.setattr("src.core.tunnel_config._read_tunnel_data", lambda: {})

    assert config.get_tunnel_id() == ""
