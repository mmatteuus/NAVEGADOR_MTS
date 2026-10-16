"""Modelos do canal de atualização."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UpdateInfo:
    """Resultado de consulta ou metadados do instalador."""

    version: str
    release_notes: str
    download_url: str
    asset_name: str
    is_newer: bool
    update_type: str = "installer"
    status: str = "ok"
    error: Optional[str] = None
    sha256: Optional[str] = None
