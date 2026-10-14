"""Suíte de Testes do Protocolo MCP e Roteador de Ferramentas.

Valida os contratos da especificação Model Context Protocol (JSON-RPC):
initialize, ping, tools/list, tools/call, bloqueio de segurança e formatação.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from src.mcp import MCPServer, MCPToolRouter, WebSocketBridge, get_browser_tools, get_computer_tools


def test_schemas_integrity() -> None:
    """Valida a conformidade e completude dos esquemas formais JSON Schema."""
    browser_tools = get_browser_tools()
    computer_tools = get_computer_tools()

    assert len(browser_tools) >= 10, "Deve conter pelo menos 10 ferramentas de navegador"
    assert len(computer_tools) >= 4, "Deve conter pelo menos 4 ferramentas de computador"

    for tool in browser_tools + computer_tools:
        assert "name" in tool and "description" in tool and "inputSchema" in tool
        assert tool["inputSchema"].get("type") == "object"
        assert "properties" in tool["inputSchema"]

    comp_names = {t["name"] for t in computer_tools}
    assert {"computer_screenshot", "computer_mouse_action", "computer_keyboard_action"}.issubset(comp_names)


def test_mcp_server_jsonrpc_lifecycle() -> None:
    """Valida o ciclo de vida JSON-RPC: initialize, initialized, ping, tools/list."""
    async def _run():
        server = MCPServer(ws_port=9123)
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        init_res = await server.handle_jsonrpc(init_req)
        assert init_res["result"]["protocolVersion"] == "2024-11-05"
        assert init_res["result"]["serverInfo"]["name"] == "browser-mcp-mts"

        notif_res = await server.handle_jsonrpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert notif_res is None

        ping_res = await server.handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        assert ping_res == {"jsonrpc": "2.0", "id": 2, "result": {}}

        list_res = await server.handle_jsonrpc({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert len(list_res["result"]["tools"]) >= 14

        unk_res = await server.handle_jsonrpc({"jsonrpc": "2.0", "id": 4, "method": "invalid/method"})
        assert unk_res["error"]["code"] == -32601

    asyncio.run(_run())


def test_router_safety_gate_blocking() -> None:
    """Valida que o roteador bloqueia ações de computador se a trava estiver desligada."""
    async def _run():
        router = MCPToolRouter(safety_checker=lambda: False)
        status_res = await router.dispatch("computer_get_status", {})
        assert not status_res["isError"]
        assert json.loads(status_res["content"][0]["text"])["authorized"] is False

        mouse_res = await router.dispatch("computer_mouse_action", {"action": "click"})
        assert mouse_res["isError"] is True
        assert "não autorizado" in mouse_res["content"][0]["text"].lower()

        router_auth = MCPToolRouter(
            safety_checker=lambda: True,
            computer_executor=lambda name, args: asyncio.sleep(0, result={"ok": True})
        )
        ok_res = await router_auth.dispatch("computer_mouse_action", {"action": "click"})
        assert ok_res["isError"] is False

    asyncio.run(_run())


def test_router_browser_disconnected_and_formatting() -> None:
    """Valida erro quando navegador desconectado e formatação de screenshot Base64."""
    async def _run():
        bridge = WebSocketBridge(port=9124)
        router = MCPToolRouter(ws_bridge=bridge)
        res = await router.dispatch("browser_navigate", {"url": "https://google.com"})
        assert res["isError"] and "não está conectada" in res["content"][0]["text"].lower()

        # Mock de imagem Base64
        bridge._active_socket = object()
        bridge.send_action = lambda a, p, timeout=30.0: asyncio.sleep(
            0, result={"base64": "iVBORw0KGgoAAAANSUhEUgAAAAE=", "width": 100}
        )
        img_res = await router.dispatch("browser_screenshot", {"format": "png"})
        assert not img_res["isError"]
        types = [c["type"] for c in img_res["content"]]
        assert "image" in types and "text" in types

    asyncio.run(_run())
