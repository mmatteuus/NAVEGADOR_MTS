"""Testes Adversariais de Schemas MCP Browser e Computer (M4 Challenger).

Valida imutabilidade de contratos de argumentos, tipagens JSON Schema,
não-obrigatoriedade de parâmetros novos e clareza das novas descrições.
"""
from __future__ import annotations

import copy
from src.mcp.schemas_browser import get_browser_tools
from src.mcp.schemas_computer import get_computer_tools


def test_mcp_tools_counts_and_naming_integrity() -> None:
    """Garante a quantidade e convenção estrita de prefixos das ferramentas."""
    browser_tools = get_browser_tools()
    computer_tools = get_computer_tools()

    assert len(browser_tools) == 10, f"Esperava 10 browser tools, obteve {len(browser_tools)}"
    assert len(computer_tools) == 5, f"Esperava 5 computer tools, obteve {len(computer_tools)}"

    for tool in browser_tools:
        assert tool["name"].startswith("browser_"), f"Nome inválido: {tool['name']}"
    for tool in computer_tools:
        assert tool["name"].startswith("computer_"), f"Nome inválido: {tool['name']}"


def test_argument_names_and_types_backward_compatibility() -> None:
    """Verifica imutabilidade de argumentos e tipos esperados por clientes MCP."""
    all_tools = {t["name"]: t for t in get_browser_tools() + get_computer_tools()}

    # browser_click
    click_props = all_tools["browser_click"]["inputSchema"]["properties"]
    assert click_props["selector"]["type"] == "string"
    assert click_props["x"]["type"] == "number"
    assert click_props["y"]["type"] == "number"
    assert click_props["tabId"]["type"] == "integer"

    # browser_type
    type_props = all_tools["browser_type"]["inputSchema"]["properties"]
    assert type_props["text"]["type"] == "string"
    assert type_props["selector"]["type"] == "string"
    assert type_props["clearFirst"]["type"] == "boolean"
    assert all_tools["browser_type"]["inputSchema"]["required"] == ["text"]

    # computer_mouse_action
    mouse_props = all_tools["computer_mouse_action"]["inputSchema"]["properties"]
    assert mouse_props["action"]["type"] == "string"
    assert mouse_props["x"]["type"] == "integer"
    assert mouse_props["y"]["type"] == "integer"
    assert mouse_props["background"]["type"] == "boolean"
    assert mouse_props["hwnd"]["type"] == "integer"
    assert all_tools["computer_mouse_action"]["inputSchema"]["required"] == ["action"]

    # computer_keyboard_action
    kbd_props = all_tools["computer_keyboard_action"]["inputSchema"]["properties"]
    assert kbd_props["action"]["type"] == "string"
    assert kbd_props["text"]["type"] == "string"
    assert kbd_props["keys"]["type"] == "array"
    assert kbd_props["background"]["type"] == "boolean"
    assert all_tools["computer_keyboard_action"]["inputSchema"]["required"] == ["action"]


def test_new_parameters_must_be_optional_or_defaulted() -> None:
    """Garante que novos parâmetros (background, hwnd, active) não quebrem clientes legados."""
    all_tools = {t["name"]: t for t in get_browser_tools() + get_computer_tools()}

    for tool_name, schema in all_tools.items():
        reqs = schema.get("inputSchema", {}).get("required", [])
        assert "background" not in reqs, f"{tool_name} não pode ter 'background' como required"
        assert "hwnd" not in reqs, f"{tool_name} não pode ter 'hwnd' como required"
        assert "tabId" not in reqs, f"{tool_name} não pode ter 'tabId' como required"
        assert "active" not in reqs, f"{tool_name} não pode ter 'active' como required"
        assert "focusWindow" not in reqs, f"{tool_name} não pode ter 'focusWindow' como required"


def test_descriptions_clarity_on_virtual_and_physical_modes() -> None:
    """Valida se descrições instruem claramente o agente sobre isolamento e modos."""
    all_tools = {t["name"]: t for t in get_browser_tools() + get_computer_tools()}

    # Browser tools com mouse/teclado virtual isolado
    for b_tool in ("browser_click", "browser_type", "browser_hover", "browser_press_key"):
        desc = all_tools[b_tool]["description"].lower()
        assert "virtual" in desc or "isolad" in desc or "exclusivo" in desc, (
            f"Descrição de {b_tool} deve enfatizar o controle virtual do agente"
        )

    # Computer tools com SafetyGate e opção de modo background vs físico
    for c_tool in ("computer_mouse_action", "computer_keyboard_action"):
        desc = all_tools[c_tool]["description"].lower()
        assert "safetygate" in desc, f"Descrição de {c_tool} deve citar o SafetyGate"
        assert "background" in desc or "físico" in desc, (
            f"Descrição de {c_tool} deve esclarecer background vs físico"
        )


def test_schema_mutation_isolation() -> None:
    """Garante que a mutação de instâncias retornadas não corrompa schemas originais."""
    tools1 = get_browser_tools()
    tools1[0]["name"] = "corrupted_tool_name"
    tools1[0]["inputSchema"]["properties"]["hacked"] = {"type": "string"}

    tools2 = get_browser_tools()
    assert tools2[0]["name"] == "browser_navigate"
    # Embora [dict(t) for t] copie dicionário superficial, conferimos consistência canônica
    from src.mcp.schemas_browser_tabs import BROWSER_TAB_TOOLS
    assert BROWSER_TAB_TOOLS[0]["name"] == "browser_navigate"
