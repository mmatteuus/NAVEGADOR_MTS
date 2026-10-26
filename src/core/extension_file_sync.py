"""Sincronização automática dos arquivos da extensão MV3 para os diretórios locais."""
from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List

logger = logging.getLogger("BrowserMTS.ExtensionSync")


def get_source_extension_dir() -> Path | None:
    """Identifica o diretório da extensão mais recente pertencente ao app em execução."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir / "extension", exe_dir / "_internal" / "extension"):
            if candidate.is_dir() and (candidate / "manifest.json").is_file():
                return candidate
    dev_dir = Path(__file__).resolve().parent.parent / "extension"
    if dev_dir.is_dir() and (dev_dir / "manifest.json").is_file():
        return dev_dir
    return None


def get_known_extension_targets() -> List[Path]:
    """Descobre locais no computador onde a extensão pode ter sido carregada desempacotada."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    candidates: List[Path] = []
    if local_app_data:
        base = Path(local_app_data) / "Programs" / "Navegador MTS"
        candidates.extend([base / "extension", base / "_internal" / "extension"])
    if app_data:
        candidates.append(Path(app_data) / "browser-mcp-mts" / "extension")
    candidates.extend([
        Path(r"D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS\src\extension"),
        Path(r"D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS\dist\NAVEGADOR_MTS\extension"),
        Path(r"D:\MATEUS\Documentos\GitHub\browser mcp mts\src\extension"),
    ])
    return candidates


def sync_extension_files() -> List[Path]:
    """Copia os arquivos da extensão para todas as pastas conhecidas na máquina."""
    src = get_source_extension_dir()
    if not src or not src.is_dir():
        logger.debug("Diretório fonte da extensão não encontrado para sincronização.")
        return []

    synced: List[Path] = []
    targets = get_known_extension_targets()
    src_resolved = src.resolve()

    for target in targets:
        try:
            target_resolved = target.resolve()
            if target_resolved == src_resolved:
                continue
            if not target.parent.exists():
                continue
            target.mkdir(parents=True, exist_ok=True)
            for root, _, files in os.walk(src):
                rel = Path(root).relative_to(src)
                dest_dir = target / rel
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in files:
                    s_file = Path(root) / f
                    d_file = dest_dir / f
                    try:
                        shutil.copy2(s_file, d_file)
                    except OSError as exc:
                        logger.debug("Falha ao copiar %s -> %s: %s", s_file, d_file, exc)
            synced.append(target)
            logger.info("Extensão sincronizada com sucesso em: %s", target)
        except Exception as exc:
            logger.debug("Erro ao sincronizar diretório de extensão %s: %s", target, exc)
    return synced
