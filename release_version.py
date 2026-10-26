"""Utilitário padronizado de ciclo de versão e build de release para agentes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from src.core.updater import DEFAULT_RELEASE_URL, GITHUB_OWNER, GITHUB_REPO, bump_version
from src.core.update_network import fetch_json, parse_version_tuple
from src.core.update_web_fallback import fetch_release_web_fallback

ROOT = Path(__file__).resolve().parent
VERSION_PATTERN = re.compile(r'^(APP_VERSION\s*=\s*["\'])([^"\']+)(["\'])$', re.MULTILINE)
ISS_PATTERN = re.compile(r'(#define\s+MyAppVersion\s+")([^"]+)(")')


def read_versions(root: Path = ROOT) -> dict[str, str]:
    """Lê as versões declaradas nos três arquivos canônicos do projeto."""
    ver_src = (root / "src" / "version.py").read_text(encoding="utf-8")
    ver_match = VERSION_PATTERN.search(ver_src)
    manifest = json.loads((root / "src" / "extension" / "manifest.json").read_text(encoding="utf-8"))
    iss_src = (root / "installer.iss").read_text(encoding="utf-8")
    iss_match = ISS_PATTERN.search(iss_src)
    return {
        "version_py": ver_match.group(2) if ver_match else "",
        "manifest_json": str(manifest.get("version", "")),
        "installer_iss": iss_match.group(2) if iss_match else "",
    }


def set_version(new_version: str, root: Path = ROOT) -> str:
    """Estampa atomicamente uma nova versão semântica nos arquivos canônicos."""
    clean = new_version.strip().lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", clean):
        raise ValueError(f"Versão inválida: {new_version}")
    ver_file = root / "src" / "version.py"
    manifest_file = root / "src" / "extension" / "manifest.json"
    iss_file = root / "installer.iss"

    ver_text, c1 = VERSION_PATTERN.subn(rf"\g<1>{clean}\g<3>", ver_file.read_text(encoding="utf-8"), count=1)
    iss_text, c2 = ISS_PATTERN.subn(rf"\g<1>{clean}\g<3>", iss_file.read_text(encoding="utf-8"), count=1)
    if c1 != 1 or c2 != 1:
        raise RuntimeError("Padrão de versão não encontrado em src/version.py ou installer.iss.")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["version"] = clean
    ver_file.write_text(ver_text, encoding="utf-8")
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    iss_file.write_text(iss_text, encoding="utf-8")
    return clean


def check_sync(root: Path = ROOT, check_remote: bool = True) -> tuple[bool, str]:
    """Verifica paridade entre os arquivos locais e superioridade frente à última release remota."""
    versions = read_versions(root)
    unique = set(versions.values())
    if len(unique) != 1 or "" in unique:
        return False, f"Divergência de versão detectada: {versions}"
    local_ver = next(iter(unique))
    if not check_remote:
        return True, f"Versão local sincronizada: {local_ver}"
    data, _ = fetch_json(DEFAULT_RELEASE_URL)
    if data is None:
        data, _ = fetch_release_web_fallback(GITHUB_OWNER, GITHUB_REPO)
    if data and data.get("tag_name"):
        remote_tag = str(data["tag_name"])
        local_key = (parse_version_tuple(local_ver) + (0, 0, 0, 0))[:4]
        remote_key = (parse_version_tuple(remote_tag) + (0, 0, 0, 0))[:4]
        if local_key <= remote_key:
            return False, f"Versão local ({local_ver}) não é superior à release remota ({remote_tag})."
        return True, f"Versão local ({local_ver}) sincronizada e superior à remota ({remote_tag})."
    return True, f"Versão local ({local_ver}) sincronizada (release remota indisponível)."


def build_release(root: Path = ROOT) -> Path:
    """Executa o pipeline completo de ícone, executável PyInstaller e instalador Inno Setup."""
    ok, msg = check_sync(root, check_remote=False)
    if not ok:
        raise RuntimeError(msg)
    version = read_versions(root)["version_py"]
    for script in ("generate_icon.py", "build_exe.py", "build_installer.py"):
        res = subprocess.run([sys.executable, str(root / script)], cwd=str(root))
        if res.returncode != 0:
            raise RuntimeError(f"Falha ao executar {script} (exit {res.returncode}).")
    installer = root / "dist_installer" / f"NAVEGADOR_MTS_Instalador_v{version}.exe"
    checksum = root / "dist_installer" / f"NAVEGADOR_MTS_Instalador_v{version}.sha256"
    if not installer.is_file() or not checksum.is_file():
        raise FileNotFoundError("Artefatos finais não encontrados em dist_installer.")
    return installer


def main(argv: list[str] | None = None) -> int:
    """Interface de linha de comando para padronização de releases."""
    parser = argparse.ArgumentParser(description="Gerenciador padronizado de versão e release do NAVEGADOR MTS.")
    parser.add_argument("--check", action="store_true", help="Verifica sincronia local e comparação com GitHub.")
    parser.add_argument("--bump", choices=("patch", "minor", "major"), help="Incrementa a versão semântica.")
    parser.add_argument("--set", dest="set_ver", help="Define explicitamente a versão (ex: 2.4.0).")
    parser.add_argument("--build", action="store_true", help="Compila ícone, executável e instalador.")
    args = parser.parse_args(argv)

    if args.set_ver:
        print(f"Versão definida para: {set_version(args.set_ver)}")
    elif args.bump:
        current = read_versions()["version_py"]
        print(f"Versão incrementada para: {set_version(bump_version(current, args.bump))}")
    if args.check:
        ok, message = check_sync()
        print(message)
        if not ok:
            return 1
    if args.build:
        artifact = build_release()
        print(f"Instalador gerado: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
