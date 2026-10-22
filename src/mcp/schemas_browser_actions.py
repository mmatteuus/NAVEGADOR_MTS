"""Módulo de Schemas para Ações e Interações no Navegador (Browser Actions MCP).

Define os esquemas formais JSON Schema para ferramentas de interação direta com
páginas web (cliques, digitação, atalhos, rolagem e execução de scripts JS).
"""

from __future__ import annotations

from typing import Any, Dict, List

BROWSER_ACTION_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "browser_click",
        "description": "Executa clique com mouse virtual exclusivo do agente na aba alvo (sem tocar no cursor físico e sem roubar foco).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Seletor CSS do elemento (ex: #btn-enviar)"},
                "ref": {"type": "string", "description": "Referência do elemento obtida via browser_snapshot"},
                "element": {"type": "string", "description": "Descrição amigável do elemento para auditoria"},
                "x": {"type": "number", "description": "Coordenada horizontal opcional para clique"},
                "y": {"type": "number", "description": "Coordenada vertical opcional para clique"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            }
        }
    },
    {
        "name": "browser_type",
        "description": "Digita no campo virtual do agente em aba liberada no popup, sem mudar foco. Use selector/ref ou o último campo do agente; recusa o campo em uso pelo usuário e editores ricos incompatíveis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Texto a ser digitado no elemento selecionado"},
                "selector": {"type": "string", "description": "Seletor CSS do campo de texto"},
                "ref": {"type": "string", "description": "Referência do elemento via browser_snapshot"},
                "clearFirst": {"type": "boolean", "default": False, "description": "Se True, limpa o texto antes"},
                "submit": {"type": "boolean", "default": False, "description": "Se True, pressiona Enter após digitar"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "browser_evaluate_js",
        "description": "Executa código JavaScript arbitrário no contexto da página e retorna o resultado serializado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "Código JavaScript a ser executado"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            },
            "required": ["script"]
        }
    },
    {
        "name": "browser_scroll",
        "description": "Rola a página web ou um elemento com rolagem interna em uma direção especificada.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "default": "down"},
                "amount": {"type": "number", "default": 400, "description": "Distância em pixels"},
                "selector": {"type": "string", "description": "Seletor CSS opcional do container rolável"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            }
        }
    },
    {
        "name": "browser_hover",
        "description": "Move o cursor do mouse virtual exclusivo do agente sobre o elemento na aba, sem alterar o cursor físico do Windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Seletor CSS do elemento"},
                "ref": {"type": "string", "description": "Referência do elemento obtida via snapshot"},
                "x": {"type": "number", "description": "Posição X relativa"},
                "y": {"type": "number", "description": "Posição Y relativa"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            }
        }
    },
    {
        "name": "browser_press_key",
        "description": "Opera o caret virtual no último campo do agente ou selector/ref, em aba liberada. Não usa foco/clipboard do usuário; atalhos incompatíveis retornam erro.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Nome da tecla (ex: Enter, Tab, Escape, Backspace)"},
                "selector": {"type": "string", "description": "Seletor CSS opcional do campo do agente"},
                "ref": {"type": "string", "description": "Referência opcional obtida via snapshot"},
                "modifiers": {"type": "array", "items": {"type": "string"}, "description": "Modificadores (Control, Alt, Shift)"},
                "tabId": {"type": "integer", "description": "ID de uma aba liberada no popup. Omitir somente com uma única aba liberada."}
            },
            "required": ["key"]
        }
    }
]

__all__ = ["BROWSER_ACTION_TOOLS", "get_browser_action_tools"]


def get_browser_action_tools() -> List[Dict[str, Any]]:
    """Retorna uma cópia da lista de ferramentas de ação do navegador."""
    return [dict(tool) for tool in BROWSER_ACTION_TOOLS]
