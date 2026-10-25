"""Concessões humanas de diretórios, exclusivas por sessão e por árvore."""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from .folder_paths import local_absolute, relative_target, root_identity


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

    def get(self, session_id):
        with self._lock:
            return self._by_session.get(session_id)

    def revoke(self, session_id):
        with self._lock:
            self._by_session.pop(session_id, None)

    def resolve(self, session_id, relative, root_id):
        with self._lock:
            grant = self._by_session.get(session_id)
            if grant is None or root_id != grant.root_id:
                raise ValueError("FOLDER_NOT_ASSIGNED: escolha uma pasta na aplicação")
            return grant, relative_target(grant.root, relative)

    @contextmanager
    def commit(self, grant):
        """Revogação e efeito final têm uma ordem única; concessões antigas expiram."""
        with self._lock:
            if self._by_session.get(grant.session_id) != grant:
                raise ValueError("FOLDER_REVOKED")
            yield

    def clear(self):
        with self._lock:
            self._by_session.clear()


folder_grants = FolderGrantRegistry()
