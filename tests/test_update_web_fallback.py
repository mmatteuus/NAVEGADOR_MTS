"""Testes para o fallback resiliente de atualização via web."""

from unittest.mock import MagicMock, patch
from src.core.update_web_fallback import fetch_release_web_fallback


def test_fetch_release_web_fallback_success():
    """Valida resolução da release quando o redirect web informa tag válida."""
    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://github.com/mmatteuus/NAVEGADOR_MTS/releases/tag/v2.3.3.236"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload, err = fetch_release_web_fallback("mmatteuus", "NAVEGADOR_MTS")

    assert err is None
    assert payload is not None
    assert payload["tag_name"] == "v2.3.3.236"
    assert len(payload["assets"]) == 1
    assert payload["assets"][0]["name"] == "NAVEGADOR_MTS_Instalador_v2.3.3.236.exe"


def test_fetch_release_web_fallback_invalid_tag():
    """Valida rejeição quando a tag no redirect não corresponde a versão válida."""
    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://github.com/mmatteuus/NAVEGADOR_MTS/releases/tag/invalid_tag"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload, err = fetch_release_web_fallback("mmatteuus", "NAVEGADOR_MTS")

    assert payload is None
    assert "Tag não encontrada" in err
