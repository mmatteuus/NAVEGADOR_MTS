"""Despachante assíncrono de mensagens e ações recebidas na ponte WebSocket."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from .session_manager import session_manager
from .ws_protocol import handle_incoming_envelope

logger = logging.getLogger("BrowserMTS.WSDispatcher")


def resolve_pending_request(data: Dict[str, Any], pending_requests: Dict[str, asyncio.Future]) -> None:
    """Resolve a Future pendente correspondente à resposta enviada pela extensão."""
    if not isinstance(data, dict):
        return
    payload = data.get("payload")
    p = payload if isinstance(payload, dict) else data
    if not isinstance(p, dict):
        return
    req_id = p.get("requestId") or data.get("id")
    if req_id and req_id in pending_requests:
        fut = pending_requests.pop(req_id)
        if not fut.done():
            if p.get("error"):
                fut.set_exception(RuntimeError(str(p["error"])))
            else:
                fut.set_result(p.get("result", p.get("data", {})))


async def dispatch_agent_action(
    data: Dict[str, Any], websocket: Any, send_action_cb: Callable[..., Any]
) -> None:
    """Processa e executa comandos agent_action com lock granular e validação de aba."""
    if not isinstance(data, dict):
        return
    call_id = data.get("id", "agent_cmd")
    raw_params = data.get("params")
    if raw_params is None:
        params: Dict[str, Any] = {}
    elif isinstance(raw_params, dict):
        params = raw_params
    else:
        err = "Parâmetros inválidos: 'params' deve ser um objeto JSON (dict)."
        await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": err}))
        return

    act = data.get("action", "")
    transport_sid = data.get("sessionId")
    forged_sid = params.get("sessionId") or params.get("session_id")
    if forged_sid is not None:
        if not transport_sid or str(forged_sid).strip() != str(transport_sid).strip():
            err_msg = "FORGERY_DENIED: Tentativa de forja de sessão detectada em params."
            logger.warning(err_msg)
            await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": err_msg}))
            return

    clean_params = {k: v for k, v in params.items() if k not in ("sessionId", "session_id")}
    session_id = transport_sid
    if session_id:
        clean_params["sessionId"] = session_id

    try:
        if act.startswith("browser_"):
            tab_id = clean_params.get("tabId")
            if tab_id is not None:
                try:
                    tid = int(tab_id)
                    if not session_manager.validate_tab_access(session_id, tid):
                        err_msg = f"TAB_ACCESS_DENIED: Acesso recusado à aba {tid}. A aba pertence a outra sessão."
                        logger.warning(err_msg)
                        await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": err_msg}))
                        return
                except (ValueError, TypeError):
                    pass

            sess = await session_manager.get_or_create_session(session_id)
            async with sess.lock:
                res = await send_action_cb(act, clean_params, session_id=session_id)

            if act == "browser_manage_tabs" and session_id:
                if clean_params.get("action") == "close":
                    close_id = clean_params.get("tabId")
                    if close_id is not None:
                        try:
                            session_manager.release_tab(int(close_id))
                        except (ValueError, TypeError):
                            pass

            success = res.get("success", True) if isinstance(res, dict) else True
            await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": success, "result": res}))
        elif act.startswith("computer_"):
            if act in ("computer_mouse_move", "computer_mouse_click", "computer_mouse_drag",
                       "computer_mouse_scroll", "computer_keyboard_type", "computer_key_press"):
                from ..computer import execute_computer_action
                res = await asyncio.to_thread(execute_computer_action, act, clean_params)
            else:
                from .computer_dispatch import execute_mcp_computer
                res = await execute_mcp_computer(act, clean_params)
            success = res.get("success", False) if isinstance(res, dict) else False
            await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": success, "result": res}))
        else:
            await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": f"Ação desconhecida: '{act}'"}))
    except Exception as exc:
        logger.error(f"Erro ao processar agent_action '{act}': {exc}")
        await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": str(exc)}))
