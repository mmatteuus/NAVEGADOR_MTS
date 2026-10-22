"""Modelos de dados para sessões concorrentes de agentes de IA."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Dict, Set


@dataclass
class AgentSession:
    """Representa a sessão isolada de um agente de IA no servidor MCP."""

    session_id: str
    agent_id: str = ""
    connected_at: float = field(default_factory=time.time)
    status: str = "active"
    assigned_tabs: Set[int] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def assign_tab(self, tab_id: int) -> None:
        """Associa uma aba do navegador exclusivamente a esta sessão."""
        self.assigned_tabs.add(tab_id)

    def release_tab(self, tab_id: int) -> None:
        """Remove a associação de uma aba desta sessão."""
        self.assigned_tabs.discard(tab_id)

    def has_tab(self, tab_id: int) -> bool:
        """Verifica se a aba informada pertence a esta sessão."""
        return tab_id in self.assigned_tabs

    def to_dict(self) -> Dict[str, Any]:
        """Serializa os metadados da sessão para consulta e auditoria."""
        return {
            "sessionId": self.session_id,
            "agentId": self.agent_id,
            "connectedAt": self.connected_at,
            "status": self.status,
            "assignedTabs": sorted(list(self.assigned_tabs)),
            "metadata": self.metadata,
        }
