"""Nomes de agentes e anúncios para a escolha humana de destinos."""
from __future__ import annotations

import asyncio
import json
import logging
import time

from .session_manager import session_manager

logger = logging.getLogger("BrowserMTS.AgentDirectory")


def agent_directory() -> list[dict]:
    """Lista sessões inicializadas; o ID distingue clientes com o mesmo nome."""
    return [{"sessionId": sid, "agentId": session.agent_id,
             "lastActivity": session.metadata.get("lastActivity", session.connected_at),
             "connected": True}
            for sid in session_manager.list_active_sessions()
            if (session := session_manager.get_session(sid)) is not None]


async def announce_agents(bridge) -> None:
    """Falha de um navegador não impede inicialização dos demais clientes."""
    if not hasattr(bridge, "registry"):
        return
    payload = json.dumps({"type": "agents_changed", "payload": {"agents": agent_directory()}})
    sockets = bridge.registry.extension_sockets()
    results = await asyncio.gather(*(sock.send(payload) for sock in sockets), return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.debug("Não foi possível anunciar agentes: %s", type(result).__name__)


async def register_agent(bridge, session_id: str, client_info=None) -> None:
    """Registra apenas o identificador determinado pelo transporte."""
    info = client_info if isinstance(client_info, dict) else {}
    name = info.get("name", "")
    name = name[:100] if isinstance(name, str) else ""
    previous = session_manager.get_session(session_id)
    changed = previous is None or (name and name != previous.agent_id)
    session = await session_manager.get_or_create_session(session_id, agent_id=name)
    if name:
        session.agent_id = name
    session.metadata["lastActivity"] = time.time()
    if changed:
        await announce_agents(bridge)


async def initialize_agent(server, session_id: str, params: dict) -> None:
    """Inicializa no hub compartilhado também para processos MCP stdio."""
    info = params.get("clientInfo", {})
    await register_agent(server.ws_bridge, session_id, info)
    if server._use_active_hub:
        from .hub_client import register_agent_with_hub
        await register_agent_with_hub(session_id, info, server.host, server.ws_port)
