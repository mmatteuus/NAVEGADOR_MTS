"""Prepara uma versão determinística somente no checkout efêmero do CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "src" / "version.py"
MANIFEST_FILE = ROOT / "src" / "extension" / "manifest.json"
VERSION_PATTERN = re.compile(r'^(APP_VERSION\s*=\s*["\'])[^"\']+(["\'])$', re.MULTILINE)


def derive_release_version(base: str, run_number: int) -> str:
    """Acrescenta o número monotônico da execução ao produto base."""
    parts = base.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("BASE_VERSION deve ter três componentes numéricos.")
    if run_number < 1 or run_number > 65535:
        raise ValueError("run_number deve estar entre 1 e 65535.")
    if any(int(part) > 65535 for part in parts):
        raise ValueError("componentes da versão não podem exceder 65535.")
    return f"{base}.{run_number}"


def stamp_version(version: str) -> None:
    """Estampa versão em fontes de build do checkout temporário."""
    source = VERSION_FILE.read_text(encoding="utf-8")
    stamped, count = VERSION_PATTERN.subn(rf'\g<1>{version}\g<2>', source, count=1)
    if count != 1:
        raise ValueError("APP_VERSION não encontrado em src/version.py.")
    VERSION_FILE.write_text(stamped, encoding="utf-8")
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifest["version"] = version
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def metadata(version: str, commit: str) -> dict[str, str]:
    """Produz metadados verificáveis para nome, tag e commit do asset."""
    if not re.fullmatch(r"\d+(?:\.\d+){3}", version):
        raise ValueError("versão de release inválida.")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit deve ser SHA-1 completo.")
    return {
        "version": version,
        "tag": f"v{version}",
        "commit": commit,
        "asset": f"NAVEGADOR_MTS_Instalador_v{version}.exe",
        "checksum_asset": f"NAVEGADOR_MTS_Instalador_v{version}.sha256",
    }


def validate_identity(data: dict[str, str], commit: str) -> None:
    """Rejeita metadados cujo tag ou SHA não pertence à execução atual."""
    if data.get("commit") != commit or data.get("tag") != f"v{data.get('version')}":
        raise ValueError("tag ou commit não correspondem à execução.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-version", required=True)
    parser.add_argument("--run-number", required=True, type=int)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    version = derive_release_version(args.base_version, args.run_number)
    stamp_version(version)
    if args.metadata:
        args.metadata.write_text(
            json.dumps(metadata(version, args.commit), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(version)


if __name__ == "__main__":
    main()
