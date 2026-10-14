"""Módulo de Verificação e Download de Atualizações do BROWSER MTS.

Responsabilidades:
- Consulta segura à API de releases para verificar novas versões.
- Comparação semântica de versões (ex: 2.0.1 > 2.0.0).
- Download em segundo plano do instalador com relatório de progresso.
- Inicialização do instalador em modo de substituição in-place sem desinstalação prévia.
"""

from dataclasses import dataclass
import json
import os
import subprocess
import tempfile
from typing import Callable, Optional
import urllib.request

APP_VERSION: str = "2.0.0"
DEFAULT_RELEASE_URL: str = "https://api.github.com/repos/mmatteuus/browser-mcp-mts/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    """Metadados de uma versão disponível para atualização."""

    version: str
    release_notes: str
    download_url: str
    asset_name: str
    is_newer: bool


def parse_version_tuple(v_str: str) -> tuple[int, ...]:
    """Converte strings como 'v2.1.0' ou '2.0.0' em tupla de inteiros comparáveis."""
    clean = v_str.strip().lstrip("vV")
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) if parts else (0, 0, 0)


def check_for_updates(api_url: str = DEFAULT_RELEASE_URL) -> Optional[UpdateInfo]:
    """Consulta a API do GitHub Releases para checar novas versões disponíveis."""
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}", "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))

        tag_name = data.get("tag_name", "")
        release_notes = data.get("body", "Melhorias de desempenho e correções gerais.")
        assets = data.get("assets", [])

        current_tup = parse_version_tuple(APP_VERSION)
        latest_tup = parse_version_tuple(tag_name)
        is_newer = latest_tup > current_tup

        download_url = ""
        asset_name = ""
        for asset in assets:
            name = asset.get("name", "")
            if name.endswith(".exe"):
                download_url = asset.get("browser_download_url", "")
                asset_name = name
                break

        return UpdateInfo(
            version=tag_name or APP_VERSION,
            release_notes=release_notes,
            download_url=download_url,
            asset_name=asset_name,
            is_newer=is_newer,
        )
    except Exception:
        return None


def download_and_launch_update(
    update_info: UpdateInfo,
    progress_callback: Optional[Callable[[float], None]] = None,
    on_ready_to_install: Optional[Callable[[], None]] = None,
) -> bool:
    """Baixa o instalador executável e o executa para atualização in-place."""
    if not update_info.download_url:
        return False

    temp_dir = tempfile.gettempdir()
    target_path = os.path.join(temp_dir, update_info.asset_name or f"BROWSER_MTS_Instalador_{update_info.version}.exe")

    req = urllib.request.Request(
        update_info.download_url,
        headers={"User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536

            while chunk := resp.read(chunk_size):
                out_file.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(min(1.0, downloaded / total_size))

        if on_ready_to_install:
            on_ready_to_install()

        # Inicia o instalador Inno Setup para atualizar sobre a instalação atual
        subprocess.Popen([target_path])
        return True
    except Exception:
        return False

