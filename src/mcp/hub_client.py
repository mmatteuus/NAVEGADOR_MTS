"""Módulo Cliente de Encaminhamento ao Hub MCP Local (Hub Client).

Quando o transporte Stdio é acionado (por exemplo, pelo Claude Desktop ou pelo Cursor)
enquanto o aplicativo desktop já está rodando em segundo plano na porta 3456,
este módulo conecta como cliente ao hub ativo e encaminha as chamadas via WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict
from websockets.asyncio.client import connect
from .session_context import get_current_session_id
from .response_formatter import format_mcp_result, format_mcp_error

logger = logging.getLogger("BrowserMTS.HubClient")


async def is_hub_running(host: str = "127.0.0.1", port: int = 3456, timeout: float = 0.5) -> bool:
    """Verifica se há um hub BROWSER MTS ativo escutando na porta especificada."""
    try:
        async with asyncio.timeout(timeout):
            async with connect(f"ws://{host}:{port}") as ws:
                await ws.send(json.dumps({"type": "ping", "ts": 1}))
                resp = await ws.recv()
                return "pong" in resp
    except Exception:
        return False


async def forward_tool_to_hub(
    tool_name: str,
    arguments: Dict[str, Any],
    host: str = "127.0.0.1",
    port: int = 3456,
    timeout: float = 30.0,
    session_id: Any = None,
) -> Dict[str, Any]:
    """Encaminha uma ferramenta (tools/call) para o hub ativo com validação anti-forja."""
    trusted_sid = session_id or get_current_session_id()

    forged_sid = arguments.get("sessionId")
    if forged_sid is None:
        forged_sid = arguments.get("session_id")
    if forged_sid is not None:
        if not trusted_sid or str(forged_sid).strip() != str(trusted_sid).strip():
            return format_mcp_error(
                "Acesso recusado: Tentativa de forja de sessão detectada (sessionId nos argumentos)."
            )

    clean_args = {k: v for k, v in arguments.items() if k not in ("sessionId", "session_id")}
    uri = f"ws://{host}:{port}"

    try:
        async with connect(uri) as ws:
            req_id = f"mcp_{uuid.uuid4().hex[:12]}"
            msg: Dict[str, Any] = {
                "type": "agent_action",
                "id": req_id,
                "action": tool_name,
                "params": clean_args,
            }
            if trusted_sid:
                msg["sessionId"] = str(trusted_sid)

            await ws.send(json.dumps(msg))
            raw_resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(raw_resp)

            if not data.get("success", False):
                err_msg = data.get("error") or data.get("result", {}).get("error", "Falha na execução")
                return format_mcp_error(err_msg)

            return format_mcp_result(data.get("result", {}))
    except Exception as exc:
        logger.error(f"Falha na comunicação com o Hub local em {uri}: {exc}")
        return format_mcp_error(f"Erro de comunicação com o BROWSER MTS: {exc}")
