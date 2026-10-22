"""Módulo Cliente de Encaminhamento ao Hub MCP Local (Hub Client).

Quando o transporte Stdio é acionado (por exemplo, pelo túnel da OpenAI para
o ChatGPT ou pelo Claude Desktop) enquanto o aplicativo desktop já está rodando
em segundo plano na porta 3456, este módulo conecta como cliente ao hub ativo
e encaminha as chamadas JSON-RPC diretamente para a extensão conectada.
"""

import asyncio
import json
import logging
from typing import Any, Dict

logger = logging.getLogger("BrowserMTS.HubClient")


async def is_hub_running(host: str = "127.0.0.1", port: int = 3456, timeout: float = 0.5) -> bool:
    """Verifica se há um hub BROWSER MTS ativo escutando na porta especificada."""
    try:
        from websockets.asyncio.client import connect
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
    """Encaminha uma ferramenta (tools/call) para o hub ativo e devolve o formato MCP."""
    import uuid
    from websockets.asyncio.client import connect

    uri = f"ws://{host}:{port}"
    try:
        async with connect(uri) as ws:
            req_id = f"mcp_{uuid.uuid4().hex[:12]}"
            effective_sid = arguments.get("sessionId") or session_id
            msg = {
                "type": "agent_action",
                "id": req_id,
                "action": tool_name,
                "params": arguments,
            }
            if effective_sid:
                msg["sessionId"] = str(effective_sid)
            await ws.send(json.dumps(msg))
            raw_resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(raw_resp)

            if not data.get("success", False):
                err_msg = data.get("error") or data.get("result", {}).get("error", "Falha na execução")
                return {"content": [{"type": "text", "text": str(err_msg)}], "isError": True}

            result_data = data.get("result", {})
            content = []
            if isinstance(result_data, dict) and ("base64" in result_data or "screenshot" in result_data):
                b64 = result_data.get("base64") or result_data.get("screenshot")
                mime = result_data.get("mimeType", "image/png")
                content.append({"type": "image", "data": str(b64), "mimeType": mime})
            else:
                txt = result_data if isinstance(result_data, str) else json.dumps(result_data, ensure_ascii=False, indent=2)
                content.append({"type": "text", "text": txt})

            return {"content": content, "isError": False}

    except Exception as exc:
        logger.error(f"Falha na comunicação com o Hub local em {uri}: {exc}")
        return {"content": [{"type": "text", "text": f"Erro de comunicação com o BROWSER MTS: {exc}"}], "isError": True}

