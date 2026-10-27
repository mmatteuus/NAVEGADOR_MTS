"""Regressões de configuração distribuível e precedência do Tunnel ID."""
from __future__ import annotations

import json
from types import SimpleNamespace

from src.core import config, tunnel_config


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


def test_save_tunnel_name_normal_and_trim(monkeypatch, tmp_path) -> None:
    """Salva nome de túnel com remoção de espaços em branco e lê atomicamente."""
    fake = SimpleNamespace(app_data_dir=tmp_path)
    monkeypatch.setattr(config, "current_config", fake)
    res = tunnel_config.save_tunnel_name("  Agente Principal  ")
    assert res == "Agente Principal"
    assert tunnel_config._read_tunnel_data()["tunnel_name"] == "Agente Principal"


def test_save_tunnel_name_truncation(monkeypatch, tmp_path) -> None:
    """Garante que o nome do túnel seja truncado em 80 caracteres."""
    fake = SimpleNamespace(app_data_dir=tmp_path)
    monkeypatch.setattr(config, "current_config", fake)
    long_name = "x" * 100
    res = tunnel_config.save_tunnel_name(long_name)
    assert res == "x" * 80
    assert len(res) == 80
    assert tunnel_config._read_tunnel_data()["tunnel_name"] == "x" * 80


def test_save_tunnel_name_none_and_empty(monkeypatch, tmp_path) -> None:
    """Trata valores None e strings vazias/espaços de forma segura."""
    fake = SimpleNamespace(app_data_dir=tmp_path)
    monkeypatch.setattr(config, "current_config", fake)
    assert tunnel_config.save_tunnel_name(None) == ""
    assert tunnel_config._read_tunnel_data()["tunnel_name"] == ""
    assert tunnel_config.save_tunnel_name("   ") == ""
    assert tunnel_config._read_tunnel_data()["tunnel_name"] == ""
