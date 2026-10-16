"""Script de Compilação do Executável Standalone Navegador MTS.

Utiliza o PyInstaller para empacotar todo o código Python, bibliotecas
de interface gráfica (CustomTkinter, Pywinstyles), pystray e winotify
em uma pasta distribuível 'dist/NAVEGADOR_MTS'.
"""

import os
import json
from pathlib import Path
import subprocess
import sys
from src.version import APP_VERSION


def build_standalone_executable() -> bool:
    """Executa o PyInstaller com todas as dependências e assets embutidos."""
    print(f"Iniciando compilação do Navegador MTS v{APP_VERSION}...")
    manifest = json.loads(Path("src/extension/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != APP_VERSION:
        raise RuntimeError("A versão da extensão diverge da versão canônica.")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=NAVEGADOR_MTS",
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
        dist_ext = os.path.join("dist", "NAVEGADOR_MTS", "extension")
        shutil.copytree(os.path.join("src", "extension"), dist_ext, dirs_exist_ok=True)
        shutil.copy2("app_icon.ico", os.path.join("dist", "NAVEGADOR_MTS", "app_icon.ico"))
        for dependency in ("tunnel-client.exe", "cloudflared.exe",
                           "cloudflared-manifest.json"):
            origin = os.path.join("BROWSER-MCP-MTS-PORTATIL", dependency)
            if not os.path.isfile(origin):
                raise FileNotFoundError(f"Dependência do túnel ausente: {dependency}")
            shutil.copy2(origin, os.path.join("dist", "NAVEGADOR_MTS", dependency))
        stdio_cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
                     "--console", "--name=NAVEGADOR_MTS_MCP", "--icon=app_icon.ico",
                     "--distpath=dist/NAVEGADOR_MTS/mcp_stdio", "stdio_entrypoint.py"]
        if subprocess.run(stdio_cmd).returncode != 0:
            raise RuntimeError("Falha ao compilar o auxiliar MCP Stdio.")
        print("Compilação concluída com sucesso! Diretório: dist/NAVEGADOR_MTS")
        return True
    else:
        print(f"Erro na compilação. Código de retorno: {result.returncode}")
        return False


if __name__ == "__main__":
    success = build_standalone_executable()
    sys.exit(0 if success else 1)
