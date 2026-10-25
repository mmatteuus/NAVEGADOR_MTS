"""Atribuição humana de janelas Win32 a sessões de agentes."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from dataclasses import dataclass
from contextlib import contextmanager
from typing import Dict, Optional

user32 = ctypes.windll.user32
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
GA_ROOT = 2


@dataclass(frozen=True)
class WindowAssignment:
    session_id: str
    hwnd: int
    thread_id: int
    pid: int
    root_hwnd: int
    generation: int = 0
    allow_focus: bool = False


def window_root(hwnd: int) -> int:
    return int(user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT) or hwnd)


def window_identity(hwnd: int) -> tuple[int, int]:
    pid = wintypes.DWORD()
    thread = int(user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid)))
    if not thread or not pid.value:
        raise ValueError("TARGET_INVALID: janela sem processo válido")
    return thread, int(pid.value)


class WindowAssignmentRegistry:
    """Registra concessões feitas pela UI; chamadas MCP não concedem janelas."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_session: Dict[str, WindowAssignment] = {}
        self._generation = 0

    def assign(self, session_id: str, hwnd: int, *, allow_focus: bool = False) -> WindowAssignment:
        sid = str(session_id or "").strip()
        target = int(hwnd or 0)
        if not sid or not target or not user32.IsWindow(wintypes.HWND(target)):
            raise ValueError("TARGET_INVALID: sessão ou janela inválida")
        thread, pid = window_identity(target)
        root = window_root(target)
        with self._lock:
            for other_sid, item in self._by_session.items():
                if other_sid != sid and (item.hwnd == target or item.root_hwnd == root):
                    raise ValueError("TARGET_IN_USE: janela já atribuída a outra sessão")
            self._generation += 1
            result = WindowAssignment(sid, target, thread, pid, root, self._generation, bool(allow_focus))
            self._by_session[sid] = result
            return result

    def resolve(self, session_id: Optional[str], hwnd: Optional[int] = None) -> int:
        sid = str(session_id or "").strip()
        with self._lock:
            item = self._by_session.get(sid)
            if item is None:
                raise ValueError("TARGET_NOT_ASSIGNED: atribuição humana necessária")
            target = int(hwnd) if hwnd is not None else item.hwnd
            if target != item.hwnd or not user32.IsWindow(wintypes.HWND(target)):
                raise ValueError("TARGET_NOT_ASSIGNED: HWND não pertence à sessão")
            if window_identity(target) != (item.thread_id, item.pid) or window_root(target) != item.root_hwnd:
                raise ValueError("TARGET_INVALID: HWND foi reutilizado")
            return target

    def validate(self, assignment: WindowAssignment) -> int:
        """Valida uma concessão capturada antes de cada efeito externo."""
        with self._lock:
            current = self._by_session.get(assignment.session_id)
            if current != assignment:
                raise ValueError("TARGET_REVOKED: atribuição foi revogada ou substituída")
        return self.resolve(assignment.session_id, assignment.hwnd)

    def release(self, session_id: str) -> None:
        with self._lock:
            self._by_session.pop(str(session_id or "").strip(), None)

    @contextmanager
    def effect(self, assignment: WindowAssignment):
        """Ordena efeito e revogação; ao revogar, nenhuma operação nova é admitida."""
        with self._lock:
            self.validate(assignment)
            from .safety_gate import safety_gate
            safety_gate.check_authorization("computer_window_action")
            yield

    def get(self, session_id: str) -> Optional[WindowAssignment]:
        with self._lock:
            return self._by_session.get(str(session_id or "").strip())

    def clear(self) -> None:
        with self._lock:
            self._by_session.clear()


window_assignments = WindowAssignmentRegistry()
