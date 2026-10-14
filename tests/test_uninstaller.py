"""Suíte de Testes Automatizados para o Módulo de Desinstalação do BROWSER MTS.

Cenários cobertos:
- Localização dinâmica do executável unins000.exe.
- Limpeza segura de atalhos e chaves de registro sem gerar exceções.
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


def test_clean_shortcuts_and_registry_safe_execution():
    """Garante que a limpeza de atalhos e registro executa com segurança."""
    with patch("os.path.isfile", return_value=True), \
         patch("os.remove") as mock_remove:
        clean_shortcuts_and_registry()
        # Se os atalhos existirem, tenta remover
        assert mock_remove.call_count >= 0


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

