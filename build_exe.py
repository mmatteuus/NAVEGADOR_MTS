"""Script de Compilação do Executável Standalone BROWSER MTS.

Utiliza o PyInstaller para empacotar todo o código Python, bibliotecas
de interface gráfica (CustomTkinter, Pywinstyles), pystray e winotify
em uma pasta distribuível 'dist/BROWSER_MTS'.
"""

import os
import subprocess
import sys


def build_standalone_executable() -> bool:
    """Executa o PyInstaller com todas as dependências e assets embutidos."""
    print("Iniciando compilação do BROWSER MTS...")

    pyinstaller_bin = os.path.join(os.path.dirname(sys.executable), "pyinstaller.exe")
    if not os.path.exists(pyinstaller_bin):
        pyinstaller_bin = "pyinstaller"

    cmd = [
        pyinstaller_bin,
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=BROWSER_MTS",
        "--icon=app_icon.ico",
        "--collect-all=customtkinter",
        "--collect-all=pystray",
        "--collect-all=winotify",
        "--collect-all=pywinstyles",
        "--collect-all=darkdetect",
        "--add-data=src/extension;extension",
        "--add-data=app_icon.ico;.",
        "entrypoint.py",
    ]

    print(f"Executando comando: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("Compilação concluída com sucesso! Diretório: dist/BROWSER_MTS")
        return True
    else:
        print(f"Erro na compilação. Código de retorno: {result.returncode}")
        return False


if __name__ == "__main__":
    success = build_standalone_executable()
    sys.exit(0 if success else 1)

