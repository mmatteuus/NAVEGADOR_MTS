"""
Módulo de Schemas das Ferramentas de Navegador (Browser MCP).

Define os esquemas formais JSON Schema para todas as ferramentas
de automação e inspeção web compatíveis com a extensão Manifest V3.
Todos os esquemas seguem estritamente a especificação Model Context Protocol.
"""
from typing import Any, Dict, List

# Lista de esquemas formais das ferramentas do navegador
BROWSER_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "browser_navigate",
        "description": "Navega para uma URL na aba ativa ou especificada e aguarda o carregamento.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL completa para navegação (ex: https://github.com)"},
                "tabId": {"type": "integer", "description": "ID opcional da aba. Se omitido, usa a aba ativa."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_click",
        "description": "Executa clique em um elemento por seletor CSS, ref de acessibilidade ou coordenadas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Seletor CSS do elemento (ex: #btn-enviar)"},
                "ref": {"type": "string", "description": "Referência do elemento obtida via browser_snapshot"},
                "element": {"type": "string", "description": "Descrição amigável do elemento para auditoria"},
                "x": {"type": "number", "description": "Coordenada horizontal opcional para clique"},
                "y": {"type": "number", "description": "Coordenada vertical opcional para clique"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
            }
        }
    },
    {
        "name": "browser_type",
        "description": "Digita texto em um campo editável com simulação natural de digitação humana.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Texto a ser digitado no elemento selecionado"},
                "selector": {"type": "string", "description": "Seletor CSS do campo de texto"},
                "ref": {"type": "string", "description": "Referência do elemento via browser_snapshot"},
                "clearFirst": {"type": "boolean", "default": False, "description": "Se True, limpa o texto antes"},
                "submit": {"type": "boolean", "default": False, "description": "Se True, pressiona Enter após digitar"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Captura a árvore de acessibilidade semântica (ARIA) da página ativa para a IA.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Captura a imagem visual da aba ativa no navegador em formato Base64.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                "quality": {"type": "integer", "minimum": 1, "maximum": 100, "default": 90}
            }
        }
    },
    {
        "name": "browser_manage_tabs",
        "description": "Gerencia abas no navegador: listar abas, alternar foco, abrir nova aba ou fechar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "new", "switch", "close"]},
                "url": {"type": "string", "description": "URL para abrir em caso de ação 'new'"},
                "tabId": {"type": "integer", "description": "ID da aba alvo para ações 'switch' ou 'close'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "browser_evaluate_js",
        "description": "Executa código JavaScript arbitrário no contexto da página e retorna o resultado serializado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "Código JavaScript a ser executado"}
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
                "selector": {"type": "string", "description": "Seletor CSS opcional do container rolável"}
            }
        }
    },
    {
        "name": "browser_hover",
        "description": "Move o cursor do mouse virtual sobre o elemento para ativar menus suspensos ou tooltips.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Seletor CSS do elemento"},
                "ref": {"type": "string", "description": "Referência do elemento obtida via snapshot"},
                "x": {"type": "number", "description": "Posição X relativa"},
                "y": {"type": "number", "description": "Posição Y relativa"}
            }
        }
    },
    {
        "name": "browser_press_key",
        "description": "Pressiona uma tecla física ou combinação de modificadores no elemento em foco.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Nome da tecla (ex: Enter, Tab, Escape, Backspace)"},
                "modifiers": {"type": "array", "items": {"type": "string"}, "description": "Modificadores (Control, Alt, Shift)"}
            },
            "required": ["key"]
        }
    }
]


def get_browser_tools() -> List[Dict[str, Any]]:
    """Retorna uma cópia da lista de ferramentas do navegador disponíveis."""
    return [dict(tool) for tool in BROWSER_TOOLS]
