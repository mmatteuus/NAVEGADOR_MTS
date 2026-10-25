"""Testes unitários para o módulo de inicialização automática (autostart)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from src.ui.autostart import is_autostart_enabled, set_autostart_enabled


def test_is_autostart_enabled_non_windows() -> None:
    """Verifica se is_autostart_enabled retorna False em sistemas não-Windows."""
    with patch.object(sys, "platform", "linux"):
        assert is_autostart_enabled() is False


def test_set_autostart_enabled_non_windows() -> None:
    """Verifica se set_autostart_enabled retorna False em sistemas não-Windows."""
    with patch.object(sys, "platform", "darwin"):
        assert set_autostart_enabled(True) is False
        assert set_autostart_enabled(False) is False


def test_is_autostart_enabled_windows_true() -> None:
    """Valida retorno True quando a chave de registro existe no Windows."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    with patch.object(sys, "platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        assert is_autostart_enabled() is True
        mock_winreg.OpenKey.assert_called_once()
        mock_winreg.QueryValueEx.assert_called_once_with(mock_key, "NavegadorMTS")


def test_is_autostart_enabled_windows_false_on_exception() -> None:
    """Valida retorno False quando ocorre exceção (chave ausente ou sem permissão)."""
    mock_winreg = MagicMock()
    mock_winreg.OpenKey.side_effect = OSError("Chave não encontrada")

    with patch.object(sys, "platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        assert is_autostart_enabled() is False


def test_set_autostart_enabled_windows_enable_script_mode() -> None:
    """Testa habilitação do autostart no Windows em modo script (sys.frozen desativado)."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    with (
        patch.object(sys, "platform", "win32"),
        patch.dict("sys.modules", {"winreg": mock_winreg}),
        patch.object(sys, "executable", "/usr/bin/python"),
    ):
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        res = set_autostart_enabled(True)
        assert res is True
        mock_winreg.SetValueEx.assert_called_once()
        args = mock_winreg.SetValueEx.call_args[0]
        assert args[1] == "NavegadorMTS"
        assert "entrypoint.py" in args[4]
        assert "--minimized" in args[4]


def test_set_autostart_enabled_windows_enable_frozen_mode() -> None:
    """Testa habilitação do autostart no Windows em modo empacotado (sys.frozen = True)."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    with (
        patch.object(sys, "platform", "win32"),
        patch.dict("sys.modules", {"winreg": mock_winreg}),
        patch.object(sys, "executable", "C:\\App\\NavegadorMTS.exe"),
        patch.object(sys, "frozen", True, create=True),
    ):
        res = set_autostart_enabled(True)
        assert res is True
        mock_winreg.SetValueEx.assert_called_once()
        args = mock_winreg.SetValueEx.call_args[0]
        assert args[4] == '"C:\\App\\NavegadorMTS.exe" --minimized'


def test_set_autostart_enabled_windows_disable_success() -> None:
    """Testa desabilitação do autostart no Windows com remoção com sucesso."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

    with patch.object(sys, "platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        res = set_autostart_enabled(False)
        assert res is True
        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "NavegadorMTS")


def test_set_autostart_enabled_windows_disable_not_found() -> None:
    """Testa desabilitação do autostart quando o valor já não existia no Registro."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
    mock_winreg.DeleteValue.side_effect = FileNotFoundError()

    with patch.object(sys, "platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        res = set_autostart_enabled(False)
        assert res is True


def test_set_autostart_enabled_windows_exception() -> None:
    """Testa retorno False quando ocorre um erro genérico ao alterar o Registro."""
    mock_winreg = MagicMock()
    mock_winreg.OpenKey.side_effect = Exception("Acesso negado")

    with patch.object(sys, "platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        res = set_autostart_enabled(True)
        assert res is False
