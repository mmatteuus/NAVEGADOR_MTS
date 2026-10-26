"""Testes E2E Opaque-Box - Tier 1: Cobertura de Funcionalidades do Navegador.

Valida os contratos MCP de automação web em segundo plano (browser_*):
gerenciamento de abas, navegação isolada, cliques, digitação e inspeção.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from src.mcp import MCPServer, MCPToolRouter


class MockBrowserBridge:
    """Simulador da extensão MV3 para validação opaca dos contratos MCP."""

    def __init__(self) -> None:
        self.is_connected = True
        self.recorded_actions: list[tuple[str, dict]] = []
        self.recorded_sessions: list[str | None] = []

    async def send_action(self, name: str, params: dict, timeout: float = 30.0,
                          session_id: str | None = None) -> dict:
        self.recorded_actions.append((name, dict(params)))
        self.recorded_sessions.append(session_id)
        if name == "browser_manage_tabs":
            act = params.get("action")
            if act == "list":
                return {"tabs": [{"id": 101, "title": "Painel MTS", "url": "https://mts.local"}]}
            return {"tabId": params.get("tabId", 102), "status": "executed"}
        if name == "browser_navigate":
            return {"tabId": params.get("tabId", 1), "navigated": True, "active": params.get("active", False)}
        if name == "browser_screenshot":
            return {"base64": "iVBORw0KGgoAAAANSUhEUgAAAAE=", "format": params.get("format", "png")}
        if name == "browser_snapshot":
            return {"nodes": [{"role": "button", "name": "Entrar", "ref": "e1"}]}
        if name == "browser_evaluate_js":
            return {"result": 42}
        return {"action": name, "success": True}


@pytest.fixture
def browser_env() -> tuple[MCPToolRouter, MockBrowserBridge]:
    """Cria ambiente isolado do roteador MCP com bridge simulada."""
    bridge = MockBrowserBridge()
    router = MCPToolRouter(ws_bridge=bridge)
    return router, bridge


def test_tier1_browser_navigation_background(browser_env) -> None:
    """Valida navegação isolada por tabId com active=False por padrão."""
    router, bridge = browser_env
    args = {"url": "https://exemplo.com/docs", "tabId": 204, "active": False}
    res = asyncio.run(router.dispatch("browser_navigate", args))
    assert not res["isError"]
    assert len(bridge.recorded_actions) == 1
    assert bridge.recorded_actions[0] == ("browser_navigate", args)


def test_tier1_browser_tab_lifecycle(browser_env) -> None:
    """Valida o ciclo completo de abas: new, list, switch e close."""
    router, bridge = browser_env
    # 1. Nova aba em segundo plano
    res_new = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "new", "url": "https://a.com"}))
    assert not res_new["isError"]
    # 2. Listagem de abas
    res_list = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "list"}))
    assert not res_list["isError"]
    assert "Painel MTS" in res_list["content"][0]["text"]
    # 3. Alternância sem roubo de foco
    res_sw = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "switch", "tabId": 101, "focusWindow": False}))
    assert not res_sw["isError"]
    # 4. Fechamento de aba
    res_cl = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "close", "tabId": 101}))
    assert not res_cl["isError"]
    assert len(bridge.recorded_actions) == 4


def test_tier1_browser_interaction_dom(browser_env) -> None:
    """Valida interações sintéticas de clique e digitação na aba alvo."""
    router, bridge = browser_env
    # Digitação com limpeza prévia e envio
    type_args = {"selector": "#usuario", "text": "agente_mts", "clearFirst": True, "tabId": 10}
    res_type = asyncio.run(router.dispatch("browser_type", type_args))
    assert not res_type["isError"]
    # Clique em botão por seletor
    click_args = {"selector": "#login-btn", "button": "left", "tabId": 10}
    res_click = asyncio.run(router.dispatch("browser_click", click_args))
    assert not res_click["isError"]
    assert bridge.recorded_actions == [("browser_type", type_args), ("browser_click", click_args)]


def test_tier1_browser_screenshot_base64_format(browser_env) -> None:
    """Valida que captura de tela retorna imagem Base64 estruturada."""
    router, _ = browser_env
    res = asyncio.run(router.dispatch("browser_screenshot", {"format": "png", "tabId": 5}))
    assert not res["isError"]
    assert res["content"][0]["type"] == "image"
    assert res["content"][0]["data"] == "iVBORw0KGgoAAAANSUhEUgAAAAE="
    assert res["content"][0]["mimeType"] == "image/png"


def test_tier1_browser_jsonrpc_server_flow(dynamic_port: int) -> None:
    """Valida o envelope JSON-RPC 2.0 de tools/call para o navegador."""
    server = MCPServer(ws_port=dynamic_port)
    bridge = MockBrowserBridge()
    server.router.ws_bridge = bridge

    req = {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "tools/call",
        "params": {"name": "browser_snapshot", "arguments": {"tabId": 1}},
    }
    response = asyncio.run(server.handle_jsonrpc(req))
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 100
    assert not response["result"]["isError"]
    assert "Entrar" in response["result"]["content"][0]["text"]
    assert bridge.recorded_sessions == [server.process_session_id]
