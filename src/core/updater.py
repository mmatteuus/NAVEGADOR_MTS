"""Módulo de Verificação e Download de Atualizações do BROWSER MTS.

Responsabilidades:
- Consulta resiliente à API de releases e fallback automático para instalador local.
- Comparação semântica de versões (ex: 2.0.1 > 2.0.0).
- Download ou cópia com barra de progresso em tempo real.
- Execução do instalador in-place com fechamento forçado de instâncias antigas.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Callable, Optional
import urllib.request
from .config import current_config

APP_VERSION: str = "2.1.1"
TARGET_UPDATE_VERSION: str = APP_VERSION
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


def find_local_installer_path() -> Optional[Path]:
    """Localiza instalador executável recente gerado localmente na máquina."""
    candidates = [
        current_config.project_root / "dist_installer" / f"NAVEGADOR_MTS_Instalador_v{APP_VERSION}.exe",
        current_config.project_root / "dist_installer" / "NAVEGADOR_MTS_Instalador_v2.1.0.exe",
        current_config.project_root / "dist_installer" / "NAVEGADOR_MTS_Instalador_v2.1.exe",
        Path(r"D:\MATEUS\Documentos\GitHub\browser mcp mts\dist_installer\NAVEGADOR_MTS_Instalador_v2.1.0.exe"),
        current_config.project_root / "dist_installer" / "NAVEGADOR_MTS_Instalador_v2.0.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Navegador MTS" / "NAVEGADOR_MTS_Instalador_v2.1.0.exe",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 1_000_000:
            return p
    return None


def check_for_updates(api_url: str = DEFAULT_RELEASE_URL, allow_local_fallback: bool = True) -> Optional[UpdateInfo]:
    """Verifica atualizações na API remota com fallback para instalador compilado local."""
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}", "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag = data.get("tag_name", "")
                notes = data.get("body", "Melhorias de desempenho e correções gerais.")
                is_newer = parse_version_tuple(tag) > parse_version_tuple(APP_VERSION)
                d_url, a_name = "", ""
                for a in data.get("assets", []):
                    if a.get("name", "").endswith(".exe"):
                        d_url, a_name = a.get("browser_download_url", ""), a.get("name", "")
                        break
                return UpdateInfo(version=tag, release_notes=notes, download_url=d_url, asset_name=a_name, is_newer=is_newer)
    except Exception:
        pass

    if api_url == DEFAULT_RELEASE_URL and allow_local_fallback:
        loc = find_local_installer_path()
        if loc and parse_version_tuple(TARGET_UPDATE_VERSION) > parse_version_tuple(APP_VERSION):
            return UpdateInfo(
                version=TARGET_UPDATE_VERSION,
                release_notes="✨ Transporte Stdio MCP integrado\n✨ Conexão nativa com ChatGPT Tunnel\n✨ Execução de aplicativos locais (Excel, etc.)",
                download_url=str(loc), asset_name=loc.name, is_newer=True
            )
    return None


def download_and_launch_update(
    update_info: UpdateInfo,
    progress_callback: Optional[Callable[[float], None]] = None,
    on_ready_to_install: Optional[Callable[[], None]] = None,
) -> bool:
    """Prepara o executável da nova versão e inicia a instalação in-place com substituição forçada."""
    if not update_info.download_url:
        return False

    temp_dir = tempfile.gettempdir()
    target_path = os.path.join(temp_dir, update_info.asset_name or f"BROWSER_MTS_Instalador_{update_info.version}.exe")

    try:
        if not update_info.download_url.startswith(("http://", "https://")):
            src_path = Path(update_info.download_url)
            if not src_path.exists():
                return False
            for step in (0.3, 0.6, 0.9):
                if progress_callback:
                    progress_callback(step)
                time.sleep(0.02)
            if src_path.resolve() != Path(target_path).resolve():
                shutil.copyfile(src_path, target_path)
            if progress_callback:
                progress_callback(1.0)
        else:
            req = urllib.request.Request(update_info.download_url, headers={"User-Agent": f"BROWSER-MTS-Updater/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded, chunk_size = 0, 65536
                while chunk := resp.read(chunk_size):
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(min(1.0, downloaded / total_size))

        # Flags Inno Setup para fechar instâncias anteriores e substituir in-place sem travar
        cmd = [target_path, "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS"]
        subprocess.Popen(cmd)
        if on_ready_to_install:
            on_ready_to_install()
        return True
    except Exception:
        return False
