"""Testes E2E Opaque-Box - Tier 4: Cenários Reais de Aplicação e Workload.

Valida 5 fluxos completos de ponta a ponta que simulam a operação diária
do agente autônomo em segundo plano, sem interrupção do usuário.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from src.mcp import MCPToolRouter


class ScenarioBridge:
    """Emulador de extensão avançado com suporte a chaveamento de estado."""

    def __init__(self) -> None:
        self.is_connected = True
        self.workflow_history: list[str] = []

    async def send_action(self, name: str, params: dict, timeout: float = 30.0) -> dict:
        self.workflow_history.append(name)
        if name == "browser_manage_tabs":
            return {"tabId": 303, "status": "created"}
        if name == "browser_evaluate_js":
            return {"title": "Documentação Oficial MTS", "version": "2.2.0"}
        if name == "browser_screenshot":
            return {"base64": "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"}
        if name == "browser_snapshot":
            return {"role": "form", "children": [{"role": "textbox", "ref": "tb1"}, {"role": "button", "ref": "bt1"}]}
        return {"success": True}


def test_tier4_scenario_1_background_research() -> None:
    """Cenário 1: Pesquisa e extração completa de dados em aba de segundo plano."""
    bridge = ScenarioBridge()
    router = MCPToolRouter(ws_bridge=bridge)

    # 1. Abre aba em segundo plano
    t_res = asyncio.run(router.dispatch("browser_manage_tabs", {"action": "new", "url": "https://mts.internal/docs"}))
    assert not t_res["isError"]
    # 2. Navega sem roubar foco do usuário (active: False)
    n_res = asyncio.run(router.dispatch("browser_navigate", {"tabId": 303, "url": "https://mts.internal/docs/api", "active": False}))
    assert not n_res["isError"]
    # 3. Extrai dados via evaluate_js
    e_res = asyncio.run(router.dispatch("browser_evaluate_js", {"tabId": 303, "script": "return document.title"}))
    assert not e_res["isError"]
    assert "Documentação Oficial MTS" in e_res["content"][0]["text"]
    # 4. Captura evidência visual
    s_res = asyncio.run(router.dispatch("browser_screenshot", {"tabId": 303, "format": "png"}))
    assert not s_res["isError"]
    assert s_res["content"][0]["type"] == "image"


def test_tier4_scenario_2_form_fill_and_aria_validation() -> None:
    """Cenário 2: Preenchimento de formulário com inspeção semântica ARIA."""
    bridge = ScenarioBridge()
    router = MCPToolRouter(ws_bridge=bridge)

    # 1. Digitação sequencial
    r_type = asyncio.run(router.dispatch("browser_type", {"tabId": 303, "selector": "#email", "text": "suporte@mts.com"}))
    assert not r_type["isError"]
    # 2. Inspeciona snapshot ARIA antes do clique
    r_snap = asyncio.run(router.dispatch("browser_snapshot", {"tabId": 303}))
    assert not r_snap["isError"]
    assert "textbox" in r_snap["content"][0]["text"]
    # 3. Submissão via tecla Enter
    r_key = asyncio.run(router.dispatch("browser_press_key", {"tabId": 303, "key": "Enter"}))
    assert not r_key["isError"]
    assert bridge.workflow_history == ["browser_type", "browser_snapshot", "browser_press_key"]


def test_tier4_scenario_3_hybrid_safe_desktop_automation() -> None:
    """Cenário 3: Fluxo híbrido (Browser + Desktop) com verificação de autorização."""
    bridge = ScenarioBridge()
    desktop_ops: list[str] = []

    def mock_desk(name: str, args: dict) -> dict:
        desktop_ops.append(name)
        return {"success": True, "data": {"status": "ok"}}

    router = MCPToolRouter(
        ws_bridge=bridge,
        computer_executor=lambda n, a: asyncio.sleep(0, result=mock_desk(n, a)),
        safety_checker=lambda: True,
    )
    # 1. Coleta dado da web
    asyncio.run(router.dispatch("browser_evaluate_js", {"tabId": 303, "script": "return 1"}))
    # 2. Valida autorização
    st = asyncio.run(router.dispatch("computer_get_status", {}))
    assert json.loads(st["content"][0]["text"])["authorized"] is True
    # 3. Executa ação Win32 segura
    res_m = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click", "x": 100, "y": 100}))
    assert not res_m["isError"]
    assert desktop_ops == ["computer_mouse_action"]


def test_tier4_scenario_4_panic_emergency_abort() -> None:
    """Cenário 4: Intervenção humana com Kill-Switch abortando o fluxo."""
    kill_active = False

    router = MCPToolRouter(
        computer_executor=lambda n, a: asyncio.sleep(0, result={"success": True}),
        safety_checker=lambda: not kill_active,
        kill_switch_checker=lambda: kill_active,
    )
    # Fluxo em andamento
    assert not asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))["isError"]
    # Disparo de pânico (3x ESC < 1.2s)
    kill_active = True
    # Próxima ação é instantaneamente abortada
    aborted = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))
    assert aborted["isError"] is True
    assert "não autorizado" in aborted["content"][0]["text"].lower()


def test_tier4_scenario_5_bridge_failure_and_recovery() -> None:
    """Cenário 5: Resiliência contra queda e reconexão da extensão."""
    bridge = ScenarioBridge()
    router = MCPToolRouter(ws_bridge=bridge)

    # 1. Chamada bem sucedida
    assert not asyncio.run(router.dispatch("browser_navigate", {"url": "https://a.com"}))["isError"]

    # 2. Extensão cai temporariamente
    bridge.is_connected = False
    fail_res = asyncio.run(router.dispatch("browser_navigate", {"url": "https://b.com"}))
    assert fail_res["isError"] is True
    assert "não está conectada" in fail_res["content"][0]["text"]

    # 3. Reconexão da extensão
    bridge.is_connected = True
    ok_res = asyncio.run(router.dispatch("browser_navigate", {"url": "https://c.com"}))
    assert not ok_res["isError"]
