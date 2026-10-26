"""Testes de unidade para o módulo de Schemas de Ações do Navegador (Browser Actions).

Valida a função get_browser_action_tools, a integridade dos schemas JSON,
a cópia independente de instâncias e a obrigatoriedade de campos contratuais.
"""

from __future__ import annotations

from src.mcp.schemas_browser_actions import (
    BROWSER_ACTION_TOOLS,
    get_browser_action_tools,
)


def test_get_browser_action_tools_returns_list_of_tools() -> None:
    """Garante que get_browser_action_tools retorna uma lista válida com todas as ferramentas de ação."""
    tools = get_browser_action_tools()
    assert isinstance(tools, list)
    assert len(tools) == len(BROWSER_ACTION_TOOLS)
    assert len(tools) == 6

    expected_names = {
        "browser_click",
        "browser_type",
        "browser_evaluate_js",
        "browser_scroll",
        "browser_hover",
        "browser_press_key",
    }
    returned_names = {tool["name"] for tool in tools}
    assert returned_names == expected_names


def test_get_browser_action_tools_returns_new_dict_copies() -> None:
    """Verifica que a lista retornada contém novos dicionários e que mutações superficiais não alteram o original."""
    tools1 = get_browser_action_tools()
    tools2 = get_browser_action_tools()

    assert tools1 is not BROWSER_ACTION_TOOLS
    assert tools1 is not tools2

    # Mutação superficial em um dicionário retornado
    tools1[0]["name"] = "mutated_name"
    assert BROWSER_ACTION_TOOLS[0]["name"] == "browser_click"

    tools3 = get_browser_action_tools()
    assert tools3[0]["name"] == "browser_click"


def test_browser_action_tools_schema_integrity() -> None:
    """Valida a estrutura formal de cada esquema de ação do navegador."""
    tools = get_browser_action_tools()
    for tool in tools:
        assert "name" in tool and isinstance(tool["name"], str)
        assert tool["name"].startswith("browser_")
        assert "description" in tool and len(tool["description"]) > 10
        assert "inputSchema" in tool
        schema = tool["inputSchema"]
        assert schema.get("type") == "object"
        assert "properties" in schema and isinstance(schema["properties"], dict)


def test_browser_action_tools_required_fields_and_enums() -> None:
    """Verifica os campos obrigatórios e restrições de enum das ferramentas de ação."""
    tools = {t["name"]: t for t in get_browser_action_tools()}

    # browser_type exige 'text'
    type_schema = tools["browser_type"]["inputSchema"]
    assert type_schema.get("required") == ["text"]
    assert "text" in type_schema["properties"]

    # browser_evaluate_js exige 'script'
    eval_schema = tools["browser_evaluate_js"]["inputSchema"]
    assert eval_schema.get("required") == ["script"]
    assert "script" in eval_schema["properties"]

    # browser_press_key exige 'key'
    press_schema = tools["browser_press_key"]["inputSchema"]
    assert press_schema.get("required") == ["key"]
    assert "key" in press_schema["properties"]

    # Enums de browser_click e browser_scroll
    click_props = tools["browser_click"]["inputSchema"]["properties"]
    assert click_props["button"]["enum"] == ["left", "right", "middle"]

    scroll_props = tools["browser_scroll"]["inputSchema"]["properties"]
    assert scroll_props["direction"]["enum"] == ["up", "down", "left", "right"]
