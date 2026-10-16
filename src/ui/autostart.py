"""Módulo de Inicialização Automática com o Windows (Autostart).

Responsabilidade exclusiva:
- Gerenciamento de inicialização automática com o Windows via Registro (HKCU\\Run).
- Consulta e alteração do valor de autostart respeitando modo empacotado (frozen) e script.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Chave do Registro do Windows para inicialização automática
_REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_APP_NAME = "NavegadorMTS"

__all__ = ["is_autostart_enabled", "set_autostart_enabled"]


def is_autostart_enabled() -> bool:
    """Verifica se o aplicativo está configurado para iniciar com o Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _REG_APP_NAME)
            return True
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """Habilita ou desabilita a inicialização automática no Registro do Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}" --minimized'
                else:
                    entrypoint = Path(__file__).resolve().parents[2] / "entrypoint.py"
                    cmd = f'"{sys.executable}" "{entrypoint}" --minimized'
                winreg.SetValueEx(key, _REG_APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, _REG_APP_NAME)
                except FileNotFoundError:
                    pass
            return True
    except Exception:
        return False
