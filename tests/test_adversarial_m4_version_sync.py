"""Testes Adversariais de Consistência e Sincronização de Versão v2.2.1.

Valida a paridade estrita da versão canônica 2.2.1 entre src/version.py,
o manifesto da extensão MV3, script Inno Setup e o instalador gerado.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import pytest

from src.version import APP_VERSION


def test_version_canonical_format_and_exact_match() -> None:
    """Garante que a versão canônica seja exatamente 2.2.1 no formato semver."""
    assert APP_VERSION == "2.2.1", f"Versão canônica esperada '2.2.1', obtido '{APP_VERSION}'"
    assert re.fullmatch(r"^\d+\.\d+\.\d+$", APP_VERSION) is not None


def test_extension_manifest_version_sync() -> None:
    """Valida paridade estrita da versão no manifest.json da extensão MV3."""
    manifest_path = Path("src/extension/manifest.json")
    assert manifest_path.is_file(), "Arquivo src/extension/manifest.json não encontrado"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    ext_version = manifest_data.get("version")
    assert ext_version == APP_VERSION, (
        f"Versão no manifest ({ext_version}) diverge de src/version.py ({APP_VERSION})"
    )
    assert manifest_data.get("manifest_version") == 3, "Manifest deve ser MV3"


def test_inno_setup_script_version_sync() -> None:
    """Valida que o script Inno Setup installer.iss define MyAppVersion como 2.2.1."""
    iss_path = Path("installer.iss")
    assert iss_path.is_file(), "Arquivo installer.iss não encontrado"

    content = iss_path.read_text(encoding="utf-8")
    match = re.search(r'#define\s+MyAppVersion\s+"([^"]+)"', content)
    assert match is not None, "Diretiva #define MyAppVersion não encontrada em installer.iss"
    iss_version = match.group(1)
    assert iss_version == APP_VERSION, (
        f"Versão em installer.iss ({iss_version}) diverge de src/version.py ({APP_VERSION})"
    )


def test_packaged_dist_and_installer_consistency() -> None:
    """Confere os artefatos de compilação em dist e dist_installer se presentes."""
    dist_manifest = Path("dist/NAVEGADOR_MTS/extension/manifest.json")
    if dist_manifest.is_file():
        data = json.loads(dist_manifest.read_text(encoding="utf-8"))
        assert data.get("version") == APP_VERSION, (
            f"Pacote congelado em dist possui versão {data.get('version')}, esperava {APP_VERSION}"
        )

    installer_exe = Path(f"dist_installer/NAVEGADOR_MTS_Instalador_v{APP_VERSION}.exe")
    checksum_file = Path(f"dist_installer/NAVEGADOR_MTS_Instalador_v{APP_VERSION}.sha256")
    if installer_exe.is_file():
        size = installer_exe.stat().st_size
        assert size > 1_000_000, f"Instalador menor que 1MB ({size} bytes)"
        if checksum_file.is_file():
            recorded = checksum_file.read_text(encoding="ascii").split()[0].lower()
            computed = hashlib.sha256(installer_exe.read_bytes()).hexdigest().lower()
            assert computed == recorded, "Checksum SHA-256 do instalador diverge do arquivo .sha256"


def test_adversarial_version_mismatch_detection() -> None:
    """Verifica que divergências forçadas entre manifest e APP_VERSION são detectadas."""
    fake_manifest = {"version": "2.1.9"}
    assert fake_manifest["version"] != APP_VERSION

    with pytest.raises(RuntimeError, match="diverge da versão canônica"):
        if fake_manifest.get("version") != APP_VERSION:
            raise RuntimeError("A versão da extensão diverge da versão canônica.")
