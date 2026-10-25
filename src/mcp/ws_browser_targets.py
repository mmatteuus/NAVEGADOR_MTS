"""Seleciona navegador pelas atribuições explícitas anunciadas pelo popup."""
from __future__ import annotations


def assigned_sockets(sockets, info_by_socket, session_id, tab_id=None):
    """IDs de guia iguais em perfis diferentes não representam o mesmo destino."""
    if not session_id:
        return []
    matches = []
    for socket in sockets:
        info = info_by_socket.get(socket, {})
        owners, grants = info.get("tabAssignments", {}), info.get("grantedTabIds", [])
        if not isinstance(owners, dict) or not isinstance(grants, list):
            continue
        for tab, owner in owners.items():
            if owner != session_id or not str(tab).isdigit() or int(tab) not in grants:
                continue
            if tab_id is None or str(tab_id) == str(tab):
                matches.append(socket)
                break
    return matches
