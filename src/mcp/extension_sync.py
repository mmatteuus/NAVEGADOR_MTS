"""Sincronização de versão entre o Desktop App e a extensão do navegador.

Após uma atualização in-place, os arquivos novos da extensão já estão em
disco, mas o Chrome/Edge continua executando a versão antiga carregada em
memória até a extensão ser recarregada. Esta política pede **uma** recarga
quando a extensão relata versão inferior à do desktop.
"""
from __future__ import annotations

from typing import Any

from ..core.update_network import parse_version_tuple


def _key(version: tuple[int, ...]) -> tuple[int, int, int, int]:
    """Normaliza tuplas de versão para comparação com zeros equivalentes."""
    return tuple((version + (0, 0, 0, 0))[:4])


class ExtensionReloadPolicy:
    """Decide se o handshake deve pedir `chrome.runtime.reload()` à extensão."""

    def __init__(self, desktop_version: str) -> None:
        self._desktop = _key(parse_version_tuple(desktop_version))
        self._requested: set[str] = set()

    def should_reload(self, client_payload: Any) -> bool:
        """Retorna True no máximo uma vez por versão antiga relatada.

        A memória por versão evita laço infinito quando a extensão foi
        carregada de outra pasta e continua antiga mesmo após recarregar.
        """
        if not isinstance(client_payload, dict):
            return False
        reported = client_payload.get("version")
        if not isinstance(reported, str) or not reported[:1].isdigit():
            return False
        if reported in self._requested or _key(parse_version_tuple(reported)) >= self._desktop:
            return False
        self._requested.add(reported)
        return True

