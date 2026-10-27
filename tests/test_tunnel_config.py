"""Regressões de configuração distribuível, precedência do Tunnel ID e exibições."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

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


@pytest.mark.parametrize(
    ("name", "tid", "expected"),
    [
        (
            "Agente Alfa",
            "tunnel_12345678901234567890123456789012",
            "Agente Alfa (tunnel_1234...9012)",
        ),
        ("Agente Beta", "", "Agente Beta"),
        (
            "",
            "tunnel_12345678901234567890123456789012",
            "tunnel_1234...9012",
        ),
        ("", "", "Não configurado"),
    ],
)
def test_get_tunnel_display_label_scenarios(monkeypatch, name: str, tid: str, expected: str) -> None:
    """Valida formato do rótulo para combinações de nome e ID do túnel."""
    monkeypatch.setattr(tunnel_config, "get_tunnel_name", lambda: name)
    monkeypatch.setattr(tunnel_config, "get_tunnel_id", lambda: tid)
    assert tunnel_config.get_tunnel_display_label() == expected
