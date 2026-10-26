"""Concessões humanas de diretórios, exclusivas por sessão e por árvore."""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from .folder_paths import local_absolute, relative_target, root_identity

TUNNEL_DEFAULT = "tunnel_default"


def _is_http_session(sid: str) -> bool:
    try:
        from ..mcp.session_manager import session_manager
        s = session_manager.get_session(sid)
        return s is not None and getattr(s, "transport", "") in ("http", "sse", "streamable_http")
    except Exception:
        return False


@dataclass(frozen=True)
class FolderGrant:
    root_id: str
    session_id: str
    root: Path
    identity: tuple


class FolderGrantRegistry:
    def __init__(self):
        self._lock = threading.RLock()
        self._by_session = {}

    def assign(self, session_id, path):
        sid = str(session_id or "").strip()
        if not sid:
            raise ValueError("FOLDER_SESSION_REQUIRED")
        root = local_absolute(path)
        identity = root_identity(root)
        with self._lock:
            for owner, other in self._by_session.items():
                if owner != sid and (root == other.root or root in other.root.parents or other.root in root.parents):
                    raise ValueError("FOLDER_IN_USE: árvore já atribuída a outro agente")
            grant = FolderGrant(uuid.uuid4().hex, sid, root, identity)
            self._by_session[sid] = grant
            return grant

    def _resolve_grant(self, session_id):
        sid = str(session_id or "").strip()
        grant = self._by_session.get(sid)
        if grant is None and (sid == TUNNEL_DEFAULT or sid.startswith("sess_") or _is_http_session(sid)):
            grant = self._by_session.get(TUNNEL_DEFAULT)
        return grant

    def get(self, session_id):
        with self._lock:
            return self._resolve_grant(session_id)

    def revoke(self, session_id):
        with self._lock:
            self._by_session.pop(str(session_id or "").strip(), None)

    def resolve(self, session_id, relative, root_id):
        with self._lock:
            grant = self._resolve_grant(session_id)
            if grant is None or root_id != grant.root_id:
                raise ValueError("FOLDER_NOT_ASSIGNED: escolha uma pasta na aplicação")
            return grant, relative_target(grant.root, relative)

    @contextmanager
    def commit(self, grant):
        with self._lock:
            current = self._resolve_grant(grant.session_id)
            if current != grant:
                raise ValueError("FOLDER_REVOKED")
            yield

    def clear(self):
        with self._lock:
            self._by_session.clear()


folder_grants = FolderGrantRegistry()
