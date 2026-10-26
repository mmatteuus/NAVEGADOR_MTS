"""Modelos de dados para sessões concorrentes de agentes de IA."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Dict, Optional, Set

AGENT_FAMILIES = ("chatgpt", "claude", "gemini", "opencode", "cursor", "codex", "generic")


def classify_agent_family(agent_id: str) -> str:
    """Classifica a família da IA a partir do identificador do cliente MCP."""
    low = (agent_id or "").strip().lower()
    if not low:
        return "generic"
    if "codex" in low:
        return "codex"
    if "chatgpt" in low or "openai" in low or "gpt" in low:
        return "chatgpt"
    if "claude" in low or "anthropic" in low:
        return "claude"
    if "gemini" in low or "aistudio" in low or "google" in low:
        return "gemini"
    if "opencode" in low:
        return "opencode"
    if "cursor" in low:
        return "cursor"
    return "generic"


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
    transport: str = "unknown"
    agent_family: str = "generic"
    pid: Optional[int] = None
    last_activity: float = field(default_factory=time.time)
    last_command: str = ""
    active_command: Optional[str] = None
    call_count: int = 0
    error_count: int = 0

    def __post_init__(self) -> None:
        if self.session_id.startswith("stdio_"):
            if self.transport == "unknown":
                self.transport = "stdio"
            parts = self.session_id.split("_")
            if self.pid is None and len(parts) >= 2 and parts[1].isdigit():
                self.pid = int(parts[1])
        elif self.session_id.startswith("sess_") and self.transport == "unknown":
            self.transport = "http"
        if self.agent_id and self.agent_family == "generic":
            self.agent_family = classify_agent_family(self.agent_id)

    def record_call_start(self, tool_name: str) -> None:
        """Registra o início de execução de uma ferramenta na sessão."""
        now = time.time()
        self.last_activity = now
        self.last_command = tool_name
        self.active_command = tool_name
        self.call_count += 1
        self.metadata["lastActivity"] = now

    def record_call_end(self, tool_name: str, is_error: bool = False) -> None:
        """Registra o término de execução de uma ferramenta e contabiliza falhas."""
        now = time.time()
        self.last_activity = now
        if tool_name:
            self.last_command = tool_name
        if self.active_command == tool_name or self.active_command is not None:
            self.active_command = None
        if is_error:
            self.error_count += 1
        self.metadata["lastActivity"] = now

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
