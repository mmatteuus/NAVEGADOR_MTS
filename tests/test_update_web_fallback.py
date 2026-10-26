"""Testes para o fallback resiliente de atualização via web."""

from unittest.mock import MagicMock, patch
from src.core.update_web_fallback import fetch_release_web_fallback


def test_fetch_release_web_fallback_success():
    """Valida resolução da release quando o redirect web informa tag válida."""
    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://github.com/mmatteuus/NAVEGADOR_MTS/releases/tag/v2.4.0.1"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload, err = fetch_release_web_fallback("mmatteuus", "NAVEGADOR_MTS")

    assert err is None
    assert payload is not None
    assert payload["tag_name"] == "v2.4.0.1"
    assert len(payload["assets"]) == 1
    assert payload["assets"][0]["name"] == "NAVEGADOR_MTS_Instalador_v2.4.0.1.exe"


def test_fetch_release_web_fallback_reads_sha256_and_uses_8s_timeout():
    """Garante que o arquivo .sha256 seja consultado com timeout de 8.0s e anexado ao digest."""
    redirect_resp = MagicMock()
    redirect_resp.geturl.return_value = "https://github.com/mmatteuus/NAVEGADOR_MTS/releases/tag/v2.4.0.2"
    redirect_resp.__enter__.return_value = redirect_resp

    expected_sha = "a" * 64
    sha_resp = MagicMock()
    sha_resp.read.return_value = f"{expected_sha}  NAVEGADOR_MTS_Instalador_v2.4.0.2.exe\n".encode("ascii")
    sha_resp.__enter__.return_value = sha_resp

    with patch("urllib.request.urlopen", side_effect=[redirect_resp, sha_resp]) as mocked_open:
        payload, err = fetch_release_web_fallback("mmatteuus", "NAVEGADOR_MTS")

    assert err is None
    assert payload is not None
    assert payload["assets"][0]["digest"] == f"sha256:{expected_sha}"
    assert mocked_open.call_args_list[1].kwargs.get("timeout") == 8.0


def test_fetch_release_web_fallback_invalid_tag():
    """Valida rejeição quando a tag no redirect não corresponde a versão válida."""
    mock_resp = MagicMock()
    mock_resp.geturl.return_value = "https://github.com/mmatteuus/NAVEGADOR_MTS/releases/tag/invalid_tag"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        payload, err = fetch_release_web_fallback("mmatteuus", "NAVEGADOR_MTS")

    assert payload is None
    assert "Tag não encontrada" in err
