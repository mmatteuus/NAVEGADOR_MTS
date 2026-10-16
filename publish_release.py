"""Publica uma release imutável; a autenticação fica somente no ambiente do CI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from prepare_release import validate_identity


def _gh(args: list[str], optional_404: bool = False) -> str | None:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    if optional_404 and ("404" in (result.stderr or "") or "not found" in (result.stderr or "").lower()):
        return None
    raise RuntimeError(result.stderr.strip() or "gh falhou sem mensagem.")


def _version(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.lstrip("v").split("."))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_remote_release(repository: str, data: dict[str, str], digest: str) -> None:
    """Confere assets e digest no schema REST estável de release."""
    raw = _gh(["api", f"repos/{repository}/releases/tags/{data['tag']}"])
    assets = json.loads(raw).get("assets", [])
    by_name = {item.get("name"): item for item in assets}
    if data["asset"] not in by_name or data["checksum_asset"] not in by_name:
        raise RuntimeError("release sem assets esperados.")
    remote_digest = (by_name[data["asset"]].get("digest") or "").removeprefix("sha256:")
    if not remote_digest or remote_digest.lower() != digest:
        raise RuntimeError("digest remoto diverge do checksum local.")


def publish(metadata_path: Path, installer_dir: Path, repository: str) -> str:
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    validate_identity(data, data["commit"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or head.stdout.strip() != data["commit"]:
        raise RuntimeError("checkout não corresponde ao commit dos metadados.")
    installer = installer_dir / data["asset"]
    checksum_file = installer_dir / data["checksum_asset"]
    if not installer.is_file() or not checksum_file.is_file():
        raise RuntimeError("instalador ou checksum ausente.")
    digest = _sha256(installer)
    recorded = checksum_file.read_text(encoding="ascii").split()[0].lower()
    if recorded != digest:
        raise RuntimeError("checksum local não corresponde ao instalador.")

    ref = _gh(["api", f"repos/{repository}/git/ref/tags/{data['tag']}", "--jq", ".object.sha"], True)
    latest_raw = _gh(["release", "view", "-R", repository, "--json", "tagName"], True)
    latest = None if not latest_raw else json.loads(latest_raw).get("tagName")
    if latest and _version(data["version"]) <= _version(latest) and ref is None:
        raise RuntimeError("release fora de ordem: já existe versão mais nova.")
    if ref is not None and ref != data["commit"]:
        raise RuntimeError("tag existente aponta para outro commit.")
    if ref is not None:
        _verify_remote_release(repository, data, digest)
        return "already-published"

    latest_flag = "true" if not latest or _version(data["version"]) > _version(latest) else "false"
    _gh([
        "release", "create", "-R", repository, data["tag"], str(installer), str(checksum_file),
        "--target", data["commit"], "--title", f"NAVEGADOR MTS {data['version']}",
        "--generate-notes", f"--latest={latest_flag}",
    ])
    _verify_remote_release(repository, data, digest)
    return "published"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--installer-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    print(publish(args.metadata, args.installer_dir, args.repository))


if __name__ == "__main__":
    main()
