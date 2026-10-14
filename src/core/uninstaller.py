"""Módulo de Desinstalação Limpa do BROWSER MTS.

Responsabilidades:
- Localização dinâmica do desinstalador nativo unins000.exe.
- Remoção de chaves de inicialização no Registro do Windows.
- Limpeza de atalhos da Área de Trabalho e Menu Iniciar.
- Acionamento seguro do desinstalador com encerramento do processo atual.
"""

import os
import subprocess
import sys
from typing import Callable, Optional


def find_uninstaller_binary() -> Optional[str]:
    """Procura pelo executável oficial do desinstalador Inno Setup."""
    exe_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(exe_dir, "unins000.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Navegador MTS\unins000.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\BROWSER MTS\unins000.exe"),
        os.path.expandvars(r"%APPDATA%\Programs\Navegador MTS\unins000.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def clean_shortcuts_and_registry() -> None:
    """Remove atalhos da Área de Trabalho, Menu Iniciar e registro de inicialização."""
    if sys.platform != "win32":
        return

    # Remove do Registro (Run)
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "NavegadorMTS")
            winreg.DeleteValue(key, "BrowserMTS")
    except Exception:
        pass

    # Atalhos na Área de Trabalho do usuário
    user_desktop = os.path.expandvars(r"%USERPROFILE%\Desktop")
    for name in ["Navegador MTS.lnk", "Extensão Chrome Navegador MTS.lnk", "BROWSER MTS.lnk", "Extensão Chrome BROWSER MTS.lnk"]:
        sc_path = os.path.join(user_desktop, name)
        if os.path.isfile(sc_path):
            try:
                os.remove(sc_path)
            except Exception:
                pass


def trigger_application_uninstall(on_shutdown_callback: Optional[Callable[[], None]] = None) -> bool:
    """Dispara o processo de desinstalação oficial e finaliza o aplicativo atual."""
    clean_shortcuts_and_registry()
    uninstaller_path = find_uninstaller_binary()

    if uninstaller_path:
        # Lança o desinstalador oficial em processo separado
        subprocess.Popen([uninstaller_path])
        if on_shutdown_callback:
            on_shutdown_callback()
        else:
            sys.exit(0)
        return True

    # Fallback para instalações manuais sem Inno Setup
    if on_shutdown_callback:
        on_shutdown_callback()
    return False

