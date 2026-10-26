"""Fallback resiliente de atualização via página web pública do GitHub.

Evita falhas de rate limit (HTTP 403) na API REST sem autenticação.
"""

from __future__ import annotations

import re
from typing import Optional
import urllib.request

from ..version import APP_VERSION


def fetch_release_web_fallback(owner: str, repo: str, timeout: float = 6.0) -> tuple[Optional[dict], Optional[str]]:
    """Resolve a última versão estável e os assets via redirecionamento público do GitHub."""
    web_url = f"https://github.com/{owner}/{repo}/releases/latest"
    req = urllib.request.Request(web_url, headers={
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) NAVEGADOR-MTS/{APP_VERSION}",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_url = resp.geturl()
            tag = final_url.split("/")[-1].strip()
            if not tag or not re.fullmatch(r"v?\d+\.\d+\.\d+(?:\.\d+)?", tag):
                return None, "Tag não encontrada no redirecionamento web."
            clean = tag.lstrip("v")
            asset_name = f"NAVEGADOR_MTS_Instalador_v{clean}.exe"
            download_url = f"https://github.com/{owner}/{repo}/releases/download/{tag}/{asset_name}"
            sha_url = f"https://github.com/{owner}/{repo}/releases/download/{tag}/NAVEGADOR_MTS_Instalador_v{clean}.sha256"
            sha256_val = None
            try:
                sha_req = urllib.request.Request(sha_url, headers={"User-Agent": f"NAVEGADOR-MTS/{APP_VERSION}"})
                with urllib.request.urlopen(sha_req, timeout=8.0) as sha_resp:
                    raw = sha_resp.read()
                    text = raw.decode("ascii", errors="ignore").strip() if isinstance(raw, (bytes, bytearray)) else ""
                    if text and re.fullmatch(r"[0-9a-fA-F]{64}", text.split()[0]):
                        sha256_val = text.split()[0].lower()
            except Exception:
                pass
            payload = {
                "tag_name": tag,
                "body": "Atualização estável disponibilizada via GitHub.",
                "draft": False,
                "prerelease": False,
                "assets": [{
                    "name": asset_name,
                    "browser_download_url": download_url,
                    "digest": f"sha256:{sha256_val}" if sha256_val else "",
                }],
            }
            return payload, None
    except Exception as exc:
        return None, f"Falha na consulta alternativa: {exc}"
