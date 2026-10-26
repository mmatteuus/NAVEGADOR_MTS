"""Canal de atualização por instalador completo do NAVEGADOR MTS."""

import os
from pathlib import Path
import subprocess
import sys
import re
from typing import Callable, Optional

from ..version import APP_VERSION
from .config import current_config
from .update_models import UpdateInfo
from .update_network import download_installer, fetch_json, parse_version_tuple

GITHUB_OWNER = "mmatteuus"
GITHUB_REPO = "NAVEGADOR_MTS"
DEFAULT_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
VERSION_MARKER = ".mts_version"


def bump_version(version: str, part: str = "patch") -> str:
    """Incrementa a parte indicada de uma versão semântica."""
    major, minor, patch = (parse_version_tuple(version) + (0, 0, 0))[:3]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _installer_version(path: Path) -> str:
    """Extrai versão do nome padronizado do instalador."""
    return path.stem.split("_v")[-1] if "_v" in path.stem else "0.0.0"


def find_local_installer_path() -> Optional[Path]:
    """Encontra o maior instalador local válido."""
    folders = [current_config.project_root / "dist_installer", Path(sys.executable).resolve().parent / "dist_installer"]
    candidates = [item for folder in folders if folder.is_dir() for item in folder.glob("NAVEGADOR_MTS_Instalador_v*.exe")]
    valid = [item for item in candidates if item.is_file() and item.stat().st_size > 1_000_000]
    return max(valid, key=lambda item: parse_version_tuple(_installer_version(item)), default=None)


def get_local_installer() -> Optional[Path]:
    """Mantém a API histórica para ferramentas locais."""
    return find_local_installer_path()


def _error(message: str, status: str = "error") -> UpdateInfo:
    return UpdateInfo(APP_VERSION, "", "", "", False, status=status, error=message)


def _version_key(version: tuple[int, ...]) -> tuple[int, int, int, int]:
    """Compara tags de três e quatro componentes com zeros equivalentes."""
    return tuple((version + (0, 0, 0, 0))[:4])


def check_for_updates(api_url: str = DEFAULT_RELEASE_URL, allow_local_fallback: bool = True) -> UpdateInfo:
    """Consulta somente releases com instalador; nunca usa ZIP da fonte."""
    data, error = fetch_json(api_url)
    if data is None and api_url == DEFAULT_RELEASE_URL:
        from .update_web_fallback import fetch_release_web_fallback
        fallback_data, _ = fetch_release_web_fallback(GITHUB_OWNER, GITHUB_REPO)
        if fallback_data is not None:
            data, error = fallback_data, None
    if data is not None:
        tag = str(data.get("tag_name", ""))
        if data.get("draft") or data.get("prerelease") or not re.fullmatch(r"v?\d+\.\d+\.\d+(?:\.\d+)?", tag):
            error = "A release encontrada não é estável ou tem tag inválida."
            data = None
    if data is not None:
        version = parse_version_tuple(tag)
        if _version_key(version) <= _version_key(parse_version_tuple(APP_VERSION)):
            return UpdateInfo(tag or APP_VERSION, data.get("body") or "", "", "", False, status="current")
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            return _error("A release possui uma lista de assets inválida.", "unavailable")
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            url = str(asset.get("browser_download_url", ""))
            expected = f"NAVEGADOR_MTS_Instalador_v{tag.lstrip('v')}.exe"
            if name == expected and url:
                digest = str(asset.get("digest") or "")
                return UpdateInfo(tag, data.get("body") or "", url, name, True,
                                  sha256=digest.removeprefix("sha256:") or None)
        error = "A release mais recente não possui instalador .exe compatível."
    if allow_local_fallback:
        local = find_local_installer_path()
        if local and _version_key(parse_version_tuple(_installer_version(local))) > _version_key(parse_version_tuple(APP_VERSION)):
            return UpdateInfo(_installer_version(local), "Instalador local disponível.", str(local), local.name, True)
    return _error(error or "Canal de atualização indisponível.", "unavailable")


def download_and_launch_update(info: UpdateInfo, progress_callback: Optional[Callable[[float], None]] = None,
                               on_ready_to_install: Optional[Callable[[], None]] = None) -> bool:
    """Valida e inicia o instalador completo no mesmo diretório da aplicação."""
    if (not info.is_newer or info.update_type != "installer" or not info.download_url
            or _version_key(parse_version_tuple(info.version)) <= _version_key(parse_version_tuple(APP_VERSION))):
        return False
    try:
        installer = download_installer(info, progress_callback)
        log_path = Path(os.environ.get("TEMP", str(Path.cwd()))) / "NAVEGADOR_MTS_installer.log"
        args = [
            str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/CURRENTUSER",
            "/NORESTART", "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS", f"/LOG={log_path}",
        ]
        if getattr(sys, "frozen", False):
            args.append(f"/DIR={Path(sys.executable).resolve().parent}")
        subprocess.Popen(args, close_fds=True)
        if on_ready_to_install:
            on_ready_to_install()
        return True
    except (OSError, IOError, ValueError):
        return False
