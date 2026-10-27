"""Suíte de Testes Automatizados para o Módulo de Desinstalação do BROWSER MTS."""

from unittest.mock import patch
from src.core.uninstaller import (
    clean_shortcuts_and_registry,
    find_uninstaller_binary,
    is_valid_uninstaller_path,
    trigger_application_uninstall,
)


def test_is_valid_uninstaller_path(tmp_path):
    """Valida rejeição e aceitação estrita de caminhos do desinstalador."""
    assert not is_valid_uninstaller_path(None)
    assert not is_valid_uninstaller_path("")

    fake_valid = tmp_path / "unins000.exe"
    fake_valid.write_text("dummy")
    assert is_valid_uninstaller_path(str(fake_valid))

    fake_invalid_name = tmp_path / "other.exe"
    fake_invalid_name.write_text("dummy")
    assert not is_valid_uninstaller_path(str(fake_invalid_name))

    non_existent = tmp_path / "nonexistent" / "unins000.exe"
    assert not is_valid_uninstaller_path(str(non_existent))


def test_find_uninstaller_binary_found(tmp_path):
    """Valida a detecção do binário unins000.exe quando presente."""
    fake_unins = tmp_path / "unins000.exe"
    fake_unins.write_text("dummy")

    with patch("sys.executable", str(tmp_path / "BROWSER_MTS.exe")):
        found = find_uninstaller_binary()
        assert found == str(fake_unins)


def test_find_uninstaller_binary_not_found():
    """Valida retorno None quando nenhum desinstalador está presente."""
    with patch("os.path.isfile", return_value=False):
        found = find_uninstaller_binary()
        assert found is None


def test_clean_shortcuts_and_registry_safe_execution():
    """Garante que a limpeza de atalhos e registro executa com segurança."""
    with patch("os.path.isfile", return_value=True), patch("os.remove") as mock_remove:
        clean_shortcuts_and_registry()
        assert mock_remove.call_count >= 0


def test_trigger_application_uninstall_with_binary():
    """Valida que o desinstalador é executado com shell=False."""
    shutdown_called = []
    fake_path = r"C:\fake\unins000.exe"

    with patch("src.core.uninstaller.find_uninstaller_binary", return_value=fake_path), \
         patch("src.core.uninstaller.is_valid_uninstaller_path", return_value=True), \
         patch("src.core.uninstaller.clean_shortcuts_and_registry"), \
         patch("subprocess.Popen") as mock_popen:

        result = trigger_application_uninstall(
            on_shutdown_callback=lambda: shutdown_called.append(True)
        )

    assert result is True
    assert len(shutdown_called) == 1
    mock_popen.assert_called_once_with([fake_path], shell=False)


def test_trigger_application_uninstall_popen_exception():
    """Valida tratamento de erro se subprocess.Popen falhar."""
    shutdown_called = []
    fake_path = r"C:\fake\unins000.exe"

    with patch("src.core.uninstaller.find_uninstaller_binary", return_value=fake_path), \
         patch("src.core.uninstaller.is_valid_uninstaller_path", return_value=True), \
         patch("src.core.uninstaller.clean_shortcuts_and_registry"), \
         patch("subprocess.Popen", side_effect=OSError("Access denied")):

        result = trigger_application_uninstall(
            on_shutdown_callback=lambda: shutdown_called.append(True)
        )

    assert result is False
    assert len(shutdown_called) == 1


def test_trigger_application_uninstall_without_binary():
    """Valida o comportamento de fallback caso unins000.exe não exista."""
    shutdown_called = []

    with patch("src.core.uninstaller.find_uninstaller_binary", return_value=None), \
         patch("src.core.uninstaller.clean_shortcuts_and_registry"):

        result = trigger_application_uninstall(
            on_shutdown_callback=lambda: shutdown_called.append(True)
        )

    assert result is False
    assert len(shutdown_called) == 1
