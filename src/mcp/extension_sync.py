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
        self._requested: set[tuple[str, str]] = set()

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
        instance = client_payload.get("instanceId")
        identity = str(instance) if isinstance(instance, str) and instance else f"legacy:{reported}"
        request_key = (identity, reported)
        if request_key in self._requested or _key(parse_version_tuple(reported)) >= self._desktop:
            return False
        self._requested.add(request_key)
        return True

    def is_outdated(self, client_payload: Any) -> bool:
        """Indica versão antiga sem provocar uma nova recarga."""
        if not isinstance(client_payload, dict):
            return False
        reported = client_payload.get("version")
        return isinstance(reported, str) and reported[:1].isdigit() and _key(parse_version_tuple(reported)) < self._desktop

