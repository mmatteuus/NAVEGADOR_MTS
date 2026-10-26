"""Testes E2E Opaque-Box - Tier 3: Combinações Cruzadas e Testes Pairwise.

Aplica matriz ortogonal de combinações entre ferramentas MCP de browser,
computer e políticas de segurança para verificar interferências mútuas.
"""
from __future__ import annotations

import asyncio
import pytest
from src.mcp import MCPToolRouter


class ComprehensiveBridgeMock:
    """Mock completo para testar interações compostas de navegador."""

    def __init__(self) -> None:
        self.is_connected = True
        self.log: list[tuple[str, dict]] = []

    async def send_action(self, name: str, params: dict, timeout: float = 30.0, **kwargs) -> dict:
        self.log.append((name, dict(params)))
        if name == "browser_manage_tabs":
            return {"tabId": 999, "action": params.get("action")}
        if name == "browser_screenshot":
            return {"base64": "QUJDREVGR0g=", "tabId": params.get("tabId")}
        if name == "browser_snapshot":
            return {"nodes": [{"ref": "r1", "role": "main"}]}
        return {"success": True, "data": params}


def test_tier3_background_nav_and_screenshot_combo() -> None:
    """Pairwise: Navegação com active=False combinada com screenshot por tabId."""
    bridge = ComprehensiveBridgeMock()
    router = MCPToolRouter(ws_bridge=bridge)

    # Passo 1: Navegação sem focar
    nav_res = asyncio.run(router.dispatch("browser_navigate", {"url": "https://mts.internal", "tabId": 12, "active": False}))
    assert not nav_res["isError"]

    # Passo 2: Screenshot imediato na mesma aba
    shot_res = asyncio.run(router.dispatch("browser_screenshot", {"tabId": 12, "format": "png"}))
    assert not shot_res["isError"]
    assert shot_res["content"][0]["type"] == "image"
    assert bridge.log == [
        ("browser_navigate", {"url": "https://mts.internal", "tabId": 12, "active": False}),
        ("browser_screenshot", {"tabId": 12, "format": "png"}),
    ]


def test_tier3_tab_creation_typing_and_click_combo() -> None:
    """Pairwise: Nova aba isolada seguida de digitação e clique de confirmação."""
    bridge = ComprehensiveBridgeMock()
    router = MCPToolRouter(ws_bridge=bridge)

    # 1. Nova aba sem ativar
    tab_res = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "new", "url": "https://portal.dev"}))
    assert not tab_res["isError"]

    # 2. Digitação com clearFirst
    type_res = asyncio.run(router.dispatch("browser_type", {"tabId": 999, "selector": "#campo", "text": "segredo123", "clearFirst": True}))
    assert not type_res["isError"]

    # 3. Clique em botão
    click_res = asyncio.run(router.dispatch("browser_click", {"tabId": 999, "selector": "#btn-confirmar"}))
    assert not click_res["isError"]
    assert len(bridge.log) == 3


def test_tier3_concurrent_browser_and_computer_status() -> None:
    """Pairwise: Execução concorrente de inspeção web e verificação de trava desktop."""
    bridge = ComprehensiveBridgeMock()
    router = MCPToolRouter(ws_bridge=bridge, safety_checker=lambda: False)

    async def _concurrent_run():
        task_browser = router.dispatch("browser_snapshot", {"tabId": 50})
        task_computer = router.dispatch("computer_get_status", {})
        return await asyncio.gather(task_browser, task_computer)

    res_b, res_c = asyncio.run(_concurrent_run())
    assert not res_b["isError"]
    assert not res_c["isError"]
    assert "r1" in res_b["content"][0]["text"]
    assert "authorized\": false" in res_c["content"][0]["text"]


def test_tier3_dynamic_authorization_lifecycle() -> None:
    """Pairwise: Transição de estado de autorização durante fluxo composto."""
    auth_state = False
    invocations: list[str] = []

    def mock_exec(name: str, args: dict) -> dict:
        invocations.append(name)
        return {"success": True, "data": {"exec": name}}

    router = MCPToolRouter(
        computer_executor=lambda n, a: asyncio.sleep(0, result=mock_exec(n, a)),
        safety_checker=lambda: auth_state,
    )

    # Tentativa 1: Bloqueada
    r1 = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))
    assert r1["isError"] is True

    # Transição: Usuário autoriza
    auth_state = True
    r2 = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))
    assert r2["isError"] is False

    # Transição: Usuário revoga
    auth_state = False
    r3 = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))
    assert r3["isError"] is True
    assert invocations == ["computer_mouse_action"]


def test_tier3_hover_and_scroll_chain() -> None:
    """Pairwise: Ação de hover para revelar container seguido de rolagem scroll."""
    bridge = ComprehensiveBridgeMock()
    router = MCPToolRouter(ws_bridge=bridge)
    h_res = asyncio.run(router.dispatch("browser_hover", {"tabId": 15, "selector": ".menu"}))
    assert not h_res["isError"]
    s_res = asyncio.run(router.dispatch("browser_scroll", {"tabId": 15, "direction": "down", "amount": 300}))
    assert not s_res["isError"]
    assert len(bridge.log) == 2

