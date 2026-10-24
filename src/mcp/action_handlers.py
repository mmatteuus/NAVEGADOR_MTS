from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from .session_manager import session_manager

logger = logging.getLogger("BrowserMTS.WSDispatcher")

async def handle_browser_action(
    act: str, clean_params: Dict[str, Any], session_id: Optional[str], call_id: str, websocket: Any, send_action_cb: Callable[..., Any]
) -> None:
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
        if clean_params.get("action") == "new":
            tid = session_manager.extract_tab_id(res)
            if tid is not None:
                session_manager.assign_tab_to_session(session_id, tid)
        elif clean_params.get("action") == "close":
            close_id = clean_params.get("tabId")
            if close_id is not None:
                try:
                    session_manager.release_tab(int(close_id))
                except (ValueError, TypeError):
                    pass

    success = res.get("success", True) if isinstance(res, dict) else True
    await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": success, "result": res}))


async def handle_computer_action(
    act: str, clean_params: Dict[str, Any], call_id: str, websocket: Any
) -> None:
    if act in ("computer_mouse_move", "computer_mouse_click", "computer_mouse_drag",
               "computer_mouse_scroll", "computer_keyboard_type", "computer_key_press"):
        from ..computer import execute_computer_action
        res = await asyncio.to_thread(execute_computer_action, act, clean_params)
    else:
        from .computer_dispatch import execute_mcp_computer
        res = await execute_mcp_computer(act, clean_params)
    success = res.get("success", False) if isinstance(res, dict) else False
    await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": success, "result": res}))
