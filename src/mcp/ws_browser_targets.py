"""Seleciona navegador pelas atribuições explícitas e heurísticas multi-navegador."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _int_set(raw: Any) -> set[int]:
    if not isinstance(raw, (list, tuple, set)):
        return set()
    return {int(item) for item in raw if str(item).lstrip("-").isdigit()}


def granted_ids(socket: Any, info_by_socket: Dict[Any, Dict[str, Any]]) -> set[int]:
    return _int_set(info_by_socket.get(socket, {}).get("grantedTabIds", []))


def open_ids(socket: Any, info_by_socket: Dict[Any, Dict[str, Any]]) -> set[int]:
    return _int_set(info_by_socket.get(socket, {}).get("openTabIds", []))


def assigned_sockets(
    sockets: Iterable[Any], info_by_socket: Dict[Any, Dict[str, Any]], session_id: Optional[str], tab_id: Any = None
) -> List[Any]:
    """IDs de guia iguais em perfis diferentes não representam o mesmo destino."""
    if not session_id:
        return []
    matches: List[Any] = []
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


def select_candidate_socket(
    sockets: List[Any], info_by_socket: Dict[Any, Dict[str, Any]],
    session_id: Optional[str] = None, tab_id: Any = None, active_socket: Any = None,
) -> Optional[Any]:
    """Desempata entre múltiplos navegadores conectados por aba, concessão ou atividade."""
    if not sockets:
        return None
    if tab_id is not None:
        try:
            tid, sid = int(tab_id), str(session_id) if session_id else None
        except (TypeError, ValueError):
            return None
        by_grant = [
            s for s in sockets if tid in granted_ids(s, info_by_socket)
            and (info_by_socket.get(s, {}).get("tabAssignments") or {}).get(str(tid)) in (None, "", sid)
        ]
        if by_grant:
            return by_grant[0] if len(by_grant) == 1 else None
        by_open = [
            s for s in sockets if tid in open_ids(s, info_by_socket)
            and str(tid) not in (info_by_socket.get(s, {}).get("tabAssignments") or {})
        ]
        return by_open[0] if len(by_open) == 1 else None
    pool = [s for s in sockets if granted_ids(s, info_by_socket)] or list(sockets)
    if len(pool) == 1:
        return pool[0]
    best_ts = max(int(info_by_socket.get(s, {}).get("lastActivatedAt") or 0) for s in pool)
    top = [s for s in pool if best_ts > 0 and int(info_by_socket.get(s, {}).get("lastActivatedAt") or 0) == best_ts]
    return top[0] if len(top) == 1 else (active_socket if active_socket in pool else pool[-1])
