"""Orquestrador de Compilação do Instalador Distribuível Windows.

Gera o executável standalone através do PyInstaller e em seguida
invoca o Inno Setup 6 para gerar o arquivo único 'NAVEGADOR_MTS_Instalador_v2.1.3.exe'.
"""

import hashlib
import os
import subprocess
import sys
from src.version import APP_VERSION
import json
from PyInstaller.archive.readers import CArchiveReader


def find_iscc_compiler() -> str:
    """Localiza o binário do compilador Inno Setup no sistema."""
    candidates = [
        r"C:\Users\MATEUS\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles%\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("Compilador Inno Setup 6 (ISCC.exe) não encontrado.")


def validate_packaged_executable(path: str) -> None:
    """Confirma archive PyInstaller e constante de src.version sem executar."""
    if not os.path.isfile(path):
        raise FileNotFoundError("Executável desktop do pacote não encontrado.")
    archive = CArchiveReader(path)
    pyz = archive.open_embedded_archive("PYZ.pyz")
    code = pyz.extract("src.version")
    if APP_VERSION not in getattr(code, "co_consts", ()):
        raise RuntimeError("A versão do executável congelado diverge da canônica.")


def build_final_installer() -> None:
    """Compila o instalador único para distribuição final."""
    print("=== Iniciando Criação do Instalador NAVEGADOR MTS ===")
    iscc_path = find_iscc_compiler()
    print(f"Compilador localizado: {iscc_path}")

    os.makedirs("dist_installer", exist_ok=True)
    packaged_manifest = os.path.join("dist", "NAVEGADOR_MTS", "extension", "manifest.json")
    if not os.path.isfile(packaged_manifest):
        raise FileNotFoundError("Pacote PyInstaller ausente; execute build_exe.py primeiro.")
    with open(packaged_manifest, encoding="utf-8") as stream:
        if json.load(stream).get("version") != APP_VERSION:
            raise RuntimeError("O pacote e a versão canônica estão divergentes.")
    validate_packaged_executable(os.path.join("dist", "NAVEGADOR_MTS", "NAVEGADOR_MTS.exe"))

    cmd = [iscc_path, f"/DMyAppVersion={APP_VERSION}", "installer.iss"]
    print(f"Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"Erro ao compilar instalador (código {result.returncode})")
        sys.exit(1)

    installer_exe = os.path.join("dist_installer", f"NAVEGADOR_MTS_Instalador_v{APP_VERSION}.exe")
    if os.path.exists(installer_exe):
        size_mb = os.path.getsize(installer_exe) / (1024 * 1024)
        hasher = hashlib.sha256()
        with open(installer_exe, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        sha_file = os.path.join("dist_installer", f"NAVEGADOR_MTS_Instalador_v{APP_VERSION}.sha256")
        with open(sha_file, "w", encoding="ascii") as sf:
            sf.write(f"{digest}  {os.path.basename(installer_exe)}\n")
        print("==================================================")
        print("SUCESSO: Instalador único gerado com perfeição!")
        print(f"Arquivo: {installer_exe}")
        print(f"Tamanho: {size_mb:.2f} MB")
        print(f"SHA-256: {digest}")
        print("==================================================")
    else:
        print("Falha: Arquivo do instalador não foi encontrado.")
        sys.exit(1)


if __name__ == "__main__":
    build_final_installer()
