"""Testes de publicação sem acesso à rede ou ao GitHub real."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from publish_release import publish


def _fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    """Cria metadata, asset e checksum coerentes para o mock."""
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    asset = asset_dir / "NAVEGADOR_MTS_Instalador_v2.1.3.417.exe"
    asset.write_bytes(b"installer")
    digest = hashlib.sha256(b"installer").hexdigest()
    (asset_dir / "NAVEGADOR_MTS_Instalador_v2.1.3.417.sha256").write_text(
        f"{digest}  {asset.name}\n", encoding="ascii"
    )
    metadata = tmp_path / "release-metadata.json"
    metadata.write_text(json.dumps({
        "version": "2.1.3.417", "tag": "v2.1.3.417", "commit": "a" * 40,
        "asset": asset.name, "checksum_asset": asset.name.replace(".exe", ".sha256"),
    }), encoding="utf-8")
    return metadata, asset_dir, asset.name


def _result(code: int, out: str = "", err: str = ""):
    """Monta resultado compatível com subprocess.run."""
    return type("Result", (), {"returncode": code, "stdout": out, "stderr": err})()


def test_tag_ausente_cria_release(tmp_path):
    """404 da tag é ausência esperada e permite criar a release."""
    metadata, asset_dir, _ = _fixture(tmp_path)
    api = json.dumps({"assets": [
        {"name": "NAVEGADOR_MTS_Instalador_v2.1.3.417.exe", "digest": "sha256:" + hashlib.sha256(b"installer").hexdigest()},
        {"name": "NAVEGADOR_MTS_Instalador_v2.1.3.417.sha256"},
    ]})
    responses = [_result(0, out="a" * 40), _result(1, err="HTTP 404"), _result(1, err="release not found"), _result(0), _result(0, out=api)]
    with patch("publish_release.subprocess.run", side_effect=responses) as run:
        assert publish(metadata, asset_dir, "owner/repo") == "published"
        assert run.call_args_list[-2].args[0][1:3] == ["release", "create"]
        assert run.call_args_list[2].args[0][0:4] == ["gh", "release", "view", "-R"]
        assert run.call_args_list[2].args[0][4] == "owner/repo"


def test_tag_existente_com_sha_diferente_bloqueia(tmp_path):
    """Uma tag imutável apontando para outro SHA nunca é sobrescrita."""
    metadata, asset_dir, _ = _fixture(tmp_path)
    responses = [_result(0, out="a" * 40), _result(0, out="b" * 40), _result(1, err="release not found")]
    with patch("publish_release.subprocess.run", side_effect=responses):
        with pytest.raises(RuntimeError, match="outro commit"):
            publish(metadata, asset_dir, "owner/repo")


def test_release_fora_de_ordem_bloqueia(tmp_path):
    """Versão menor que a latest não pode promover um release antigo."""
    metadata, asset_dir, _ = _fixture(tmp_path)
    responses = [_result(0, out="a" * 40), _result(1, err="HTTP 404"), _result(0, out='{"tagName":"v2.1.3.418"}')]
    with patch("publish_release.subprocess.run", side_effect=responses):
        with pytest.raises(RuntimeError, match="fora de ordem"):
            publish(metadata, asset_dir, "owner/repo")
