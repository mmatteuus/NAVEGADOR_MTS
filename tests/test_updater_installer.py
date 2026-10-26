"""Regressões do instalador completo e da validação do asset."""

from unittest.mock import patch

from src.core import updater
from src.core.update_network import download_installer


def _pe_stub():
    """Monta um cabeçalho PE mínimo para o teste."""
    data = bytearray(96)
    data[:2] = b"MZ"
    data[0x3C:0x40] = (64).to_bytes(4, "little")
    data[64:68] = b"PE\0\0"
    return bytes(data)


def test_asset_without_pe_signature_is_rejected(tmp_path, monkeypatch):
    """Um arquivo que não é PE nunca deve ser iniciado."""
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    source = tmp_path / "setup.exe"
    source.write_bytes(b"texto")
    next_ver = updater.bump_version(updater.APP_VERSION)
    info = updater.UpdateInfo(next_ver, "", str(source), source.name, True)
    with patch("subprocess.Popen") as launch:
        assert updater.download_and_launch_update(info) is False
    launch.assert_not_called()


def test_asset_digest_is_checked(tmp_path, monkeypatch):
    """O digest informado pela release precisa coincidir com o download."""
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    source = tmp_path / "setup.exe"
    source.write_bytes(_pe_stub())
    info = updater.UpdateInfo("2.1.4", "", str(source), source.name, True, sha256="0" * 64)
    try:
        download_installer(info)
    except IOError as exc:
        assert "SHA-256" in str(exc)
    else:
        raise AssertionError("Digest inválido foi aceito")


def test_frozen_update_targets_executable_directory(tmp_path, monkeypatch):
    """O instalador recebe a pasta do EXE, não o diretório _MEIPASS."""
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    source = tmp_path / "setup.exe"
    source.write_bytes(_pe_stub())
    next_ver = updater.bump_version(updater.APP_VERSION)
    info = updater.UpdateInfo(next_ver, "", str(source), source.name, True)
    exe = tmp_path / "NAVEGADOR_MTS.exe"
    monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updater.sys, "executable", str(exe))
    with patch("subprocess.Popen") as launch:
        assert updater.download_and_launch_update(info)
    command = launch.call_args.args[0]
    assert f"/DIR={tmp_path}" in command
    assert "/CURRENTUSER" in command
    assert "/SILENT" in command
    assert "/SUPPRESSMSGBOXES" in command
    assert "/CLOSEAPPLICATIONS" in command
    assert "/FORCECLOSEAPPLICATIONS" in command
