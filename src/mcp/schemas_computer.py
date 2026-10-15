"""
Módulo de Schemas das Ferramentas de Computador (Computer Use MCP).

Define os esquemas formais JSON Schema para todas as ferramentas
de controle e observação do sistema operacional Windows 11.
Todas as ferramentas de computador operam sob a Trava de Segurança (Safety Gate).
"""
from typing import Any, Dict, List

# Lista de esquemas formais das ferramentas do computador
COMPUTER_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "computer_screenshot",
        "description": "Captura a imagem da tela inteira do Windows ou de região multi-monitor em Base64.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                "quality": {"type": "integer", "minimum": 1, "maximum": 100, "default": 90},
                "monitorIndex": {"type": "integer", "description": "Índice do monitor (0 para principal)"},
                "region": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"}
                    },
                    "description": "Região retangular opcional para recorte da captura"
                }
            }
        }
    },
    {
        "name": "computer_mouse_action",
        "description": "Executa ações de mouse no Windows (movimento suave Bézier, cliques e arrastos).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move", "click", "double_click", "right_click", "middle_click", "drag"],
                    "description": "Tipo de ação do mouse a executar"
                },
                "x": {"type": "integer", "description": "Coordenada X na tela virtual"},
                "y": {"type": "integer", "description": "Coordenada Y na tela virtual"},
                "end_x": {"type": "integer", "description": "Coordenada X final para ações de drag"},
                "end_y": {"type": "integer", "description": "Coordenada Y final para ações de drag"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_keyboard_action",
        "description": "Executa digitação Unicode ABNT2, envio de teclas físicas e atalhos combinados no Windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["type", "press", "hotkey"],
                    "description": "Tipo de ação de teclado a ser realizada"
                },
                "text": {"type": "string", "description": "Texto Unicode a ser digitado (suporta acentos/cedilha)"},
                "key": {"type": "string", "description": "Tecla individual (ex: Enter, Tab, Escape, Backspace)"},
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de teclas para atalhos simultâneos (ex: ['Control', 'c'])"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_get_status",
        "description": "Informa se o controle do computador está autorizado pelo usuário e status do Kill-Switch.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "computer_launch_app",
        "description": "Inicia um aplicativo local no Windows (ex: excel, notepad, calc) via Shell nativo do sistema operacional.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "Nome ou caminho do aplicativo a ser iniciado (ex: excel, notepad)"}
            },
            "required": ["app"]
        }
    }
]


def get_computer_tools() -> List[Dict[str, Any]]:
    """Retorna uma cópia da lista de ferramentas de computador disponíveis."""
    return [dict(tool) for tool in COMPUTER_TOOLS]
