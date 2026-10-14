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

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
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
        import shutil
        dist_ext = os.path.join("dist", "BROWSER_MTS", "extension")
        shutil.copytree(os.path.join("src", "extension"), dist_ext, dirs_exist_ok=True)
        shutil.copy2("app_icon.ico", os.path.join("dist", "BROWSER_MTS", "app_icon.ico"))
        print("Compilação concluída com sucesso! Diretório: dist/BROWSER_MTS")
        return True
    else:
        print(f"Erro na compilação. Código de retorno: {result.returncode}")
        return False


if __name__ == "__main__":
    success = build_standalone_executable()
    sys.exit(0 if success else 1)

