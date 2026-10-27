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


def test_save_tunnel_id_invalid_format_raises_value_error() -> None:
    """Testa que formatos inválidos de tunnel_id lançam ValueError."""
    import pytest
    from src.core.tunnel_config import save_tunnel_id

    invalid_ids = [
        "",
        "invalid_id",
        "tunnel_12345",  # Menos de 32 hexadecimais
        "tunnel_" + "a" * 31,  # 31 chars
        "tunnel_" + "a" * 33,  # 33 chars
        "tunnel_" + "z" * 32,  # 'z' não é hexadecimal
        "PREFIX_tunnel_" + "a" * 32,
    ]
    for tid in invalid_ids:
        with pytest.raises(ValueError, match="ID do túnel deve ter prefixo tunnel_"):
            save_tunnel_id(tid)


def test_save_tunnel_id_valid_saves_data(monkeypatch, tmp_path) -> None:
    """Testa o salvamento de um tunnel_id válido com remoção de espaços nas pontas."""
    from types import SimpleNamespace
    from src.core import config
    from src.core.tunnel_config import save_tunnel_id, _read_tunnel_data

    fake = SimpleNamespace(app_data_dir=tmp_path)
    monkeypatch.setattr(config, "current_config", fake)

    valid_id = "tunnel_" + "f" * 32
    save_tunnel_id(f"  {valid_id}\n ")

    data = _read_tunnel_data()
    assert data.get("tunnel_id") == valid_id
