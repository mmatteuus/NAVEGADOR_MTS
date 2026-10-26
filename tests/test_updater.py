"""Suíte de Testes Automatizados do Sistema de Atualizações do BROWSER MTS.

Cenários cobertos:
- Comparação semântica de versões (parse_version_tuple).
- Consulta mockada da API GitHub Releases com detecção de versão mais recente.
- Tratamento resiliente de falhas de rede (timeouts e erros HTTP).
- Download e disparo do instalador in-place sem desinstalação.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from src.core.updater import (
    APP_VERSION,
    UpdateInfo,
    check_for_updates,
    download_and_launch_update,
    parse_version_tuple,
)


def _pe_stub(size=100):
    """Monta o menor cabeçalho PE necessário para o teste de integridade."""
    data = bytearray(max(size, 96))
    data[:2] = b"MZ"
    data[0x3C:0x40] = (64).to_bytes(4, "little")
    data[64:68] = b"PE\0\0"
    return bytes(data)


def test_parse_version_tuple_variants():
    """Valida a conversão de strings de versão em tuplas numéricas comparáveis."""
    assert parse_version_tuple("2.0.0") == (2, 0, 0)
    assert parse_version_tuple("v2.1.0") == (2, 1, 0)
    assert parse_version_tuple("V3.0.4.1") == (3, 0, 4, 1)
    assert parse_version_tuple("v2.1.0") > parse_version_tuple("2.0.0")
    assert parse_version_tuple("2.0.0") == parse_version_tuple("v2.0.0")
    assert parse_version_tuple("invalid") == (0, 0, 0)


def test_check_for_updates_newer_version_detected():
    """Valida a identificação correta de uma versão mais nova disponível."""
    mock_payload = {
        "tag_name": "v2.5.0",
        "body": "Nova versão com auto-update in-place e melhorias.",
        "assets": [
            {
                "name": "NAVEGADOR_MTS_Instalador_v2.5.0.exe",
                "browser_download_url": "https://github.com/mock/installer.exe",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest")

    assert info is not None
    assert info.version == "v2.5.0"
    assert info.is_newer is True
    assert info.download_url == "https://github.com/mock/installer.exe"
    assert "auto-update" in info.release_notes


def test_check_for_updates_same_version():
    """Valida que versão idêntica ou inferior não é marcada como newer."""
    mock_payload = {
        "tag_name": f"v{APP_VERSION}",
        "body": "Versão atual.",
        "assets": [],
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        info = check_for_updates("https://mock.api/latest")

    assert info is not None
    assert info.is_newer is False


def test_check_for_updates_network_failure_is_visible():
    """Garante que a falha de rede fica explícita para a interface."""
    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        info = check_for_updates("https://mock.api/latest")
    assert info is not None
    assert info.status == "unavailable"
    assert info.error


def test_download_and_launch_update_flow(tmp_path):
    """Valida o ciclo completo de download em chunks e acionamento do instalador."""
    info = UpdateInfo(
        version="v2.5.0",
        release_notes="Notas",
        download_url="https://mock.api/download.exe",
        asset_name="Instalador_Teste.exe",
        is_newer=True,
    )

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": "100"}
    # Simula 2 chunks de 50 bytes
    payload = _pe_stub(100)
    mock_resp.read.side_effect = [payload[:50], payload[50:], b""]
    mock_resp.__enter__.return_value = mock_resp

    progress_reports = []
    ready_called = []

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch("subprocess.Popen") as mock_popen, \
         patch("tempfile.gettempdir", return_value=str(tmp_path)):

        success = download_and_launch_update(
            info,
            progress_callback=lambda p: progress_reports.append(p),
            on_ready_to_install=lambda: ready_called.append(True),
        )

    assert success is True
    assert len(progress_reports) == 2
    assert progress_reports[-1] == 1.0
    assert len(ready_called) == 1
    mock_popen.assert_called_once()


def test_download_and_launch_update_local_file(tmp_path):
    """Valida cópia e lançamento do instalador quando download_url é local."""
    installer = tmp_path / "Instalador_Local.exe"
    installer.write_bytes(_pe_stub(52))
    info = UpdateInfo("2.5.0", "Notas", str(installer), "Instalador_Local.exe", True)

    reports = []
    with patch("subprocess.Popen") as mock_popen, \
         patch("tempfile.gettempdir", return_value=str(tmp_path)):
        ok = download_and_launch_update(info, progress_callback=lambda p: reports.append(p))

    assert ok is True
    assert reports[-1] == 1.0
    mock_popen.assert_called_once()

