"""
Pacote Servidor MCP Unificado (Model Context Protocol).

Exporta os componentes centrais para exposição de ferramentas de automação
web e controle de computador a agentes de Inteligência Artificial:
- MCPServer: Servidor principal suportando transporte Stdio e WebSocket.
- MCPToolRouter: Roteador dinâmico de ferramentas com trava de segurança.
- WebSocketBridge: Ponte de comunicação local com a extensão do navegador.
- Schemas formais JSON Schema para ferramentas browser_* e computer_*.
"""

from .router import MCPToolRouter
from .schemas_browser import BROWSER_TOOLS, get_browser_tools
from .schemas_computer import COMPUTER_TOOLS, get_computer_tools
from .server import MCPServer
from .ws_bridge import WebSocketBridge

__all__ = [
    "MCPServer",
    "MCPToolRouter",
    "WebSocketBridge",
    "BROWSER_TOOLS",
    "get_browser_tools",
    "COMPUTER_TOOLS",
    "get_computer_tools",
]
