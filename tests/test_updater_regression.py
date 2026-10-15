"""Cenários adicionais de atualização local sem sobrescrever arquivos parciais."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core import updater


def test_latest_local_installer_selected(tmp_path, monkeypatch):
    """Versões são escolhidas por número, não por nome ou data do arquivo."""
    folder = tmp_path / "dist_installer"
    folder.mkdir()
    for version in ("2.1.0", "2.2.0", "2.10.0"):
        (folder / f"NAVEGADOR_MTS_Instalador_v{version}.exe").write_bytes(
            b"MZ" + b"x" * 1_000_005)
    monkeypatch.setattr(updater, "current_config", SimpleNamespace(project_root=tmp_path))
    assert updater.find_local_installer_path().name.endswith("v2.10.0.exe")
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        info = updater.check_for_updates()
    assert info is not None and info.is_newer
    assert info.version == "2.10.0"


def test_incomplete_download_never_launches(tmp_path):
    """Download truncado não deve iniciar um executável inválido."""
    info = updater.UpdateInfo("3.0", "Notas", "https://example.test/setup.exe",
                              "NAVEGADOR_MTS_Instalador_v3.0.exe", True)
    response = MagicMock()
    response.headers = {"Content-Length": "100"}
    response.read.side_effect = [b"A" * 20, b""]
    response.__enter__.return_value = response

    with patch("tempfile.gettempdir", return_value=str(tmp_path)), \
         patch("urllib.request.urlopen", return_value=response), \
         patch("subprocess.Popen") as launch:
        assert updater.download_and_launch_update(info) is False
    launch.assert_not_called()
    assert not (tmp_path / (info.asset_name + ".part")).exists()
