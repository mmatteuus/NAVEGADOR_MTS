"""Regressões para tags de release e payloads malformados."""

from unittest.mock import MagicMock, patch

from src.core import updater


def _response(payload):
    response = MagicMock(status=200)
    response.read.return_value = __import__("json").dumps(payload).encode()
    response.__enter__.return_value = response
    return response


def test_four_component_release_asset_is_detected():
    """A versão de execução do CI deve ser aceita como release estável."""
    payload = {"tag_name": "v2.4.1.1", "assets": [{
        "name": "NAVEGADOR_MTS_Instalador_v2.4.1.1.exe",
        "browser_download_url": "https://example/setup.exe",
    }]}
    with patch("urllib.request.urlopen", return_value=_response(payload)):
        info = updater.check_for_updates(allow_local_fallback=False)
    assert info.is_newer is True
    assert info.asset_name.endswith("v2.4.1.1.exe")


def test_malformed_assets_are_reported():
    """Assets que não são lista não podem travar a consulta."""
    with patch("urllib.request.urlopen", return_value=_response({"tag_name": "v2.5.0", "assets": {}})):
        info = updater.check_for_updates(allow_local_fallback=False)
    assert info.status == "unavailable"
    assert "assets" in info.error
