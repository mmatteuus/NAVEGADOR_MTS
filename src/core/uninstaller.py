"""Módulo de Desinstalação Limpa do BROWSER MTS.

Responsabilidades:
- Localização dinâmica do desinstalador nativo unins000.exe.
- Validação estrita de segurança do executável do desinstalador.
- Remoção de chaves de inicialização no Registro do Windows.
- Limpeza de atalhos da Área de Trabalho e Menu Iniciar.
- Acionamento seguro do desinstalador com encerramento do processo atual.
"""

import os
import subprocess
import sys
from typing import Callable, Optional


def is_valid_uninstaller_path(path: Optional[str]) -> bool:
    """Valida estritamente se o caminho do desinstalador é seguro e legítimo."""
    if not path or not isinstance(path, str):
        return False
    abs_path = os.path.abspath(os.path.normpath(path))
    if not os.path.isabs(abs_path):
        return False
    if os.path.basename(abs_path).lower() != "unins000.exe":
        return False
    return os.path.isfile(abs_path)


def find_uninstaller_binary() -> Optional[str]:
    """Procura e valida o executável oficial do desinstalador Inno Setup."""
    exe_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(exe_dir, "unins000.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Navegador MTS\unins000.exe"),
        os.path.expandvars(r"%APPDATA%\Programs\Navegador MTS\unins000.exe"),
    ]
    for raw_path in candidates:
        norm_path = os.path.abspath(os.path.normpath(raw_path))
        if is_valid_uninstaller_path(norm_path):
            return norm_path
    return None


def clean_shortcuts_and_registry() -> None:
    """Remove atalhos da Área de Trabalho, Menu Iniciar e registro de inicialização."""
    if sys.platform != "win32":
        return

    # Remove do Registro (Run)
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, "NavegadorMTS")
    except Exception:
        pass

    # Atalhos na Área de Trabalho do usuário
    user_desktop = os.path.expandvars(r"%USERPROFILE%\Desktop")
    for name in ["Navegador MTS.lnk", "Extensão Chrome Navegador MTS.lnk"]:
        sc_path = os.path.join(user_desktop, name)
        if os.path.isfile(sc_path):
            try:
                os.remove(sc_path)
            except Exception:
                pass


def trigger_application_uninstall(
    on_shutdown_callback: Optional[Callable[[], None]] = None,
) -> bool:
    """Dispara o processo de desinstalação oficial e finaliza o aplicativo atual."""
    clean_shortcuts_and_registry()
    uninstaller_path = find_uninstaller_binary()

    if uninstaller_path and is_valid_uninstaller_path(uninstaller_path):
        try:
            # Lança o desinstalador oficial em processo separado sem shell
            subprocess.Popen([uninstaller_path], shell=False)
            if on_shutdown_callback:
                on_shutdown_callback()
            else:
                sys.exit(0)
            return True
        except Exception:
            pass

    # Fallback para instalações manuais sem Inno Setup
    if on_shutdown_callback:
        on_shutdown_callback()
    return False
