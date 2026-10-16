"""Consulta e transferência segura do instalador oficial."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import struct
from typing import Callable, Optional
import urllib.request

from ..version import APP_VERSION
from .update_models import UpdateInfo


def parse_version_tuple(value: str) -> tuple[int, ...]:
    """Converte uma versão em tupla numérica."""
    clean = str(value).strip().lstrip("vV").split("+")[0]
    parts = []
    for part in clean.split("."):
        if not part.isdigit():
            break
        parts.append(int(part))
    return tuple(parts) if parts else (0, 0, 0)


def fetch_json(url: str, timeout: float = 6.0) -> tuple[Optional[dict], Optional[str]]:
    """Consulta JSON e preserva a causa útil para a interface."""
    request = urllib.request.Request(url, headers={
        "User-Agent": f"NAVEGADOR-MTS-Updater/{APP_VERSION}",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None, f"Servidor retornou HTTP {response.status}."
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                return None, "Resposta de atualização inválida."
            return payload, None
    except Exception as exc:
        return None, f"Não foi possível consultar atualizações: {exc}"


def _is_pe(path: Path) -> bool:
    """Confirma a assinatura DOS de um executável Windows."""
    try:
        with path.open("rb") as stream:
            if stream.read(2) != b"MZ":
                return False
            stream.seek(0x3C)
            header = stream.read(4)
            if len(header) != 4:
                return False
            stream.seek(struct.unpack("<I", header)[0])
            return stream.read(4) == b"PE\0\0"
    except OSError:
        return False


def download_installer(info: UpdateInfo, progress: Optional[Callable[[float], None]] = None) -> Path:
    """Baixa/copia em arquivo temporário exclusivo e valida PE/digest."""
    temp_dir = Path(tempfile.gettempdir())
    suffix = Path(info.asset_name or "NAVEGADOR_MTS.exe").suffix or ".exe"
    fd, staged_name = tempfile.mkstemp(prefix="mts-update-", suffix=f"{suffix}.part", dir=temp_dir)
    os.close(fd)
    staged = Path(staged_name)
    final = staged.with_suffix("")
    try:
        total = done = 0
        if info.download_url.startswith(("http://", "https://")):
            request = urllib.request.Request(info.download_url, headers={"User-Agent": f"NAVEGADOR-MTS/{APP_VERSION}"})
            with urllib.request.urlopen(request, timeout=60) as response, staged.open("wb") as output:
                total = int(response.headers.get("Content-Length", 0) or 0)
                done = 0
                while chunk := response.read(65536):
                    output.write(chunk)
                    done += len(chunk)
                    if progress and total and done < total:
                        progress(min(1.0, done / total))
                if total and done != total:
                    raise IOError("Download incompleto.")
        else:
            shutil.copyfile(Path(info.download_url), staged)
        if not _is_pe(staged):
            raise IOError("O asset baixado não é um executável Windows válido.")
        if info.sha256:
            digest = hashlib.sha256(staged.read_bytes()).hexdigest().lower()
            if digest != info.sha256.lower():
                raise IOError("A assinatura SHA-256 do instalador não confere.")
        os.replace(staged, final)
        if progress:
            progress(1.0)
        return final
    except Exception:
        staged.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise
