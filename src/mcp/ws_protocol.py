"""Protocolo de handshake e respostas da ponte por conexão."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict
from ..core.updater import APP_VERSION
from .agent_directory import agent_directory, register_agent
from .session_manager import session_manager
from .ws_agent_identity import resolve_agent_identity

logger = logging.getLogger("BrowserMTS.WSProtocol")

async def handle_incoming_envelope(data: Dict[str, Any], websocket: Any, bridge: Any) -> None:
    """Interpreta envelopes JSON da extensão ou de agentes externos de IA."""
    from .ws_action_dispatcher import resolve_pending_request, dispatch_agent_action
    if not isinstance(data, dict):
        logger.warning(f"Envelope JSON inválido recebido (esperado dict, recebido {type(data).__name__})")
        return
    mtype = data.get("type")
    if not isinstance(mtype, str):
        return
    if mtype == "client_hello":
        raw_info = data.get("payload")
        info = raw_info if isinstance(raw_info, dict) else {}
        bridge.registry.register_extension(websocket, info)
        outdated = bridge._reload_policy.is_outdated(info)
        reply = {"type": "server_hello", "payload": {
            "status": "connected", "desktopVersion": APP_VERSION, "heartbeatIntervalMs": 4000,
            "agents": agent_directory(),
            "reloadRequired": bridge._reload_policy.should_reload(info),
            "extensionUpdateRequired": outdated,
            "extensionUpdateMessage": (
                "A extensão antiga foi recarregada. Se continuar desatualizada, remova a extensão carregada de outra pasta "
                "e carregue a pasta extension instalada junto ao NAVEGADOR MTS."
                if outdated else ""
            )
        }}
        await websocket.send(json.dumps(reply))
    elif mtype == "agent_hello":
        info = data.get("payload")
        info = info if isinstance(info, dict) else {}
        sid = resolve_agent_identity(bridge, websocket, info.get("sessionId"))
        bridge.registry.register_agent(websocket)
        await register_agent(bridge, sid, info.get("clientInfo"))
        await websocket.send(json.dumps({"type": "agent_registered", "sessionId": sid}))
    elif mtype == "ping":
        ts = data.get("ts", int(time.time() * 1000))
        await websocket.send(json.dumps({"type": "pong", "ts": ts, "serverTs": int(time.time() * 1000)}))
    elif mtype == "pong":
        cts = data.get("clientTs", 0)
        if cts > 0:
            bridge.last_latency_ms = max(0.0, (time.time() * 1000) - cts)
    elif mtype in ("messageResponse", "browser_response"):
        payload = data.get("payload")
        request = (payload.get("requestId") if isinstance(payload, dict) else None) or data.get("id")
        if bridge._request_sockets.get(request) is websocket:
            resolve_pending_request(data, bridge._pending_requests)
    elif mtype == "agent_action":
        bridge.registry.register_agent(websocket)
        try:
            data = {**data, "sessionId": resolve_agent_identity(bridge, websocket, data.get("sessionId"))}
        except ValueError as exc:
            await websocket.send(json.dumps({"type": "agent_response", "id": data.get("id"),
                                            "success": False, "error": str(exc)}))
            return
        await session_manager.get_or_create_session(data["sessionId"])
        await dispatch_agent_action(data, websocket, bridge.send_action)
