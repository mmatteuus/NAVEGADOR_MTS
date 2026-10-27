"""Suíte de Testes Automatizados para o Módulo de Desinstalação do BROWSER MTS.

Cenários cobertos:
- Localização dinâmica do executável unins000.exe.
- Limpeza segura de atalhos e chaves de registro sem gerar exceções.
- Tratamento de exceções ao interagir com winreg e remoção de atalhos.
- Disparo do desinstalador oficial e invocação do callback de encerramento.
"""

from unittest.mock import MagicMock, patch
import pytest
from src.core.uninstaller import (
    clean_shortcuts_and_registry,
    find_uninstaller_binary,
    trigger_application_uninstall,
)


def test_find_uninstaller_binary_found(tmp_path):
    """Valida a detecção do binário unins000.exe quando presente."""
    fake_unins = tmp_path / "unins000.exe"
    fake_unins.write_text("dummy")

    with patch("os.path.isfile", side_effect=lambda p: str(p) == str(fake_unins)):
        with patch("sys.executable", str(tmp_path / "BROWSER_MTS.exe")):
            found = find_uninstaller_binary()
            assert found == str(fake_unins)


def test_find_uninstaller_binary_not_found():
    """Valida retorno None quando nenhum desinstalador está presente."""
    with patch("os.path.isfile", return_value=False):
        found = find_uninstaller_binary()
        assert found is None


def test_clean_shortcuts_and_registry_winreg_exception():
    """Valida resiliência quando remoção no registro lança exceção em win32."""
    mock_winreg = MagicMock()
    mock_winreg.OpenKey.side_effect = RuntimeError("Falha de permissão no Registro")

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"winreg": mock_winreg}), \
         patch("os.path.isfile", return_value=False):
        clean_shortcuts_and_registry()
        mock_winreg.OpenKey.assert_called_once()


def test_clean_shortcuts_and_registry_win32_success():
    """Valida remoção com sucesso no registro e atalhos em ambiente win32."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"winreg": mock_winreg}), \
         patch("os.path.isfile", return_value=True), \
         patch("os.remove") as mock_remove:
        clean_shortcuts_and_registry()

        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "NavegadorMTS")
        assert mock_remove.call_count == 2


def test_clean_shortcuts_and_registry_shortcut_remove_exception():
    """Valida resiliência quando a remoção de atalhos lança exceção."""
    mock_winreg = MagicMock()

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"winreg": mock_winreg}), \
         patch("os.path.isfile", return_value=True), \
         patch("os.remove", side_effect=OSError("Permissão negada")):
        clean_shortcuts_and_registry()


def test_trigger_application_uninstall_with_binary():
    """Valida que o desinstalador é executado e o aplicativo encerrado."""
    shutdown_called = []

    with patch("src.core.uninstaller.find_uninstaller_binary", return_value=r"C:\fake\unins000.exe"), \
         patch("src.core.uninstaller.clean_shortcuts_and_registry"), \
         patch("subprocess.Popen") as mock_popen:

        result = trigger_application_uninstall(on_shutdown_callback=lambda: shutdown_called.append(True))

    assert result is True
    assert len(shutdown_called) == 1
    mock_popen.assert_called_once_with([r"C:\fake\unins000.exe"])


def test_trigger_application_uninstall_without_binary():
    """Valida o comportamento de fallback caso unins000.exe não exista."""
    shutdown_called = []

    with patch("src.core.uninstaller.find_uninstaller_binary", return_value=None), \
         patch("src.core.uninstaller.clean_shortcuts_and_registry"):

        result = trigger_application_uninstall(on_shutdown_callback=lambda: shutdown_called.append(True))

    assert result is False
    assert len(shutdown_called) == 1
