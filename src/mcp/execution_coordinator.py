"""Coordenador de concorrência granular para múltiplas IAs operando em paralelo."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional
from .session_models import AgentSession

_tab_locks: Dict[int, asyncio.Lock] = {}
_hwnd_locks: Dict[int, asyncio.Lock] = {}
_physical_lock: asyncio.Lock = asyncio.Lock()


class ExecutionCoordinator:
    """Gerencia locks granulares por aba (browser), HWND (background) e dispositivo físico."""

    def __init__(self) -> None:
        self._tab_locks = _tab_locks
        self._hwnd_locks = _hwnd_locks
        self._physical_lock = _physical_lock

    def get_tab_lock(self, tab_id: int) -> asyncio.Lock:
        """Retorna ou cria o lock assíncrono associado a um tabId específico."""
        tid = int(tab_id)
        if tid not in self._tab_locks:
            self._tab_locks[tid] = asyncio.Lock()
        return self._tab_locks[tid]

    def get_hwnd_lock(self, hwnd: int) -> asyncio.Lock:
        """Retorna ou cria o lock assíncrono associado a uma janela Win32 (HWND)."""
        target = int(hwnd)
        if target not in self._hwnd_locks:
            self._hwnd_locks[target] = asyncio.Lock()
        return self._hwnd_locks[target]

    @property
    def physical_lock(self) -> asyncio.Lock:
        """Retorna o lock global para mouse/teclado físico (background=False)."""
        return self._physical_lock

    def resolve_lock(
        self, session: Optional[AgentSession], tool_name: str, args: Dict[str, Any]
    ) -> Optional[asyncio.Lock]:
        """Determina o lock granular aplicável sem bloquear sessões independentes."""
        if tool_name.startswith("browser_"):
            raw_tab = args.get("tabId")
            if raw_tab is not None:
                try:
                    return self.get_tab_lock(int(raw_tab))
                except (ValueError, TypeError):
                    return None
            if session is not None and len(session.assigned_tabs) == 1:
                return self.get_tab_lock(next(iter(session.assigned_tabs)))
            return None

        if tool_name.startswith("computer_"):
            if tool_name in ("computer_get_status", "computer_folder_action"):
                return None
            bg = bool(args.get("background", True))
            if not bg:
                return self._physical_lock
            raw_hwnd = args.get("hwnd")
            if raw_hwnd is None and session is not None:
                try:
                    from ..computer.window_assignments import window_assignments
                    assignment = window_assignments.get(session.session_id)
                    if assignment is not None:
                        raw_hwnd = assignment.hwnd
                except Exception:
                    raw_hwnd = None
            if raw_hwnd is not None:
                try:
                    return self.get_hwnd_lock(int(raw_hwnd))
                except (ValueError, TypeError):
                    return None
        return None

    def clear(self) -> None:
        """Limpa os dicionários de locks (útil para testes)."""
        self._tab_locks.clear()
        self._hwnd_locks.clear()


execution_coordinator = ExecutionCoordinator()


@asynccontextmanager
async def coordinate_execution(
    session: Optional[AgentSession], tool_name: str, args: Optional[Dict[str, Any]] = None
) -> AsyncIterator[ExecutionCoordinator]:
    """Context manager assíncrono que rastreia telemetria da sessão e aplica lock granular."""
    clean_args = args if isinstance(args, dict) else {}
    lock = execution_coordinator.resolve_lock(session, tool_name, clean_args)
    if session is not None:
        session.record_call_start(tool_name)
    is_error = False
    try:
        if lock is not None:
            async with lock:
                yield execution_coordinator
        else:
            yield execution_coordinator
    except Exception:
        is_error = True
        raise
    finally:
        if session is not None:
            session.record_call_end(tool_name, is_error=is_error)
