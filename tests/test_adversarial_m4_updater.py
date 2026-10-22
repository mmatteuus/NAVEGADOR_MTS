"""Testes Adversariais do Sistema de Atualização (M4 Challenger).

Valida os cenários de comparação de versões remotas frente à versão local 2.3.1.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from src.core.updater import (
    APP_VERSION,
    UpdateInfo,
    check_for_updates,
    download_and_launch_update,
    parse_version_tuple,
    _version_key,
)


def _mock_github_release(tag: str, assets: list[dict] | None = None, draft: bool = False, prerelease: bool = False) -> MagicMock:
    """Gera um mock seguro da resposta da API de releases do GitHub."""
    payload = {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "body": f"Notas da release {tag}",
        "assets": assets if assets is not None else [
            {"name": f"NAVEGADOR_MTS_Instalador_v{tag.lstrip('v')}.exe",
             "browser_download_url": f"https://mock.cdn/NAVEGADOR_MTS_Instalador_v{tag.lstrip('v')}.exe"}
        ],
    }
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    return resp


@pytest.mark.parametrize("old_version", ["1.0.0", "2.0.0", "2.1.0", "v2.1.9", "2.1.9.9", "2.2.0", "2.2.0.41", "2.2.1"])
def test_updater_rejects_older_versions_than_current(old_version: str) -> None:
    """Garante que qualquer versão menor que a atual seja classificada como current."""
    assert APP_VERSION == "2.3.1"
    assert _version_key(parse_version_tuple(old_version)) < _version_key(parse_version_tuple(APP_VERSION))

    mock_resp = _mock_github_release(old_version)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest", allow_local_fallback=False)

    assert info.is_newer is False
    assert info.status == "current"


@pytest.mark.parametrize("same_version", ["2.3.1", "v2.3.1", "2.3.1.0"])
def test_updater_rejects_identical_version(same_version: str) -> None:
    """Garante que a versão idêntica à instalada não seja marcada para update."""
    assert APP_VERSION == "2.3.1"
    mock_resp = _mock_github_release(same_version)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest", allow_local_fallback=False)

    assert info.is_newer is False
    assert info.status == "current"


@pytest.mark.parametrize("new_version", ["2.3.1.1", "2.3.2", "v2.4.0", "3.0.0"])
def test_updater_accepts_newer_version_with_valid_asset(new_version: str) -> None:
    """Garante que versões genuinamente superiores ativem o canal de update."""
    assert APP_VERSION == "2.3.1"
    assert _version_key(parse_version_tuple(new_version)) > _version_key(parse_version_tuple(APP_VERSION))

    mock_resp = _mock_github_release(new_version)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest", allow_local_fallback=False)

    assert info.is_newer is True
    assert info.version == new_version
    assert "NAVEGADOR_MTS_Instalador_v" in info.asset_name
    assert info.download_url.startswith("https://mock.cdn/")


def test_updater_rejects_newer_version_without_compatible_installer() -> None:
    """Garante recusa de update superior quando o asset for incompatível (ex: zip ou tar)."""
    bad_assets = [{"name": "source_code.zip", "browser_download_url": "https://mock.cdn/src.zip"}]
    mock_resp = _mock_github_release("v2.4.0", assets=bad_assets)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest", allow_local_fallback=False)

    assert info.is_newer is False
    assert info.status == "unavailable"
    assert "não possui instalador .exe compatível" in info.error


def test_updater_downgrade_prevention_on_launch() -> None:
    """Valida bloqueio em download_and_launch_update se a versão for menor ou igual à atual."""
    for version in ("2.1.0", "2.1.9", "2.2.0", "2.2.0.41", "2.2.1", "v2.3.0"):
        info = UpdateInfo(
            version=version,
            release_notes="Notas",
            download_url="https://mock.api/installer.exe",
            asset_name="NAVEGADOR_MTS_Instalador_v2.3.0.exe",
            is_newer=True,  # Forçado para testar guarda interna
        )
        with patch("subprocess.Popen") as mock_launch:
            launched = download_and_launch_update(info)
            assert launched is False, f"Deveria recusar downgrade/mesma versão para {version}"
            mock_launch.assert_not_called()
