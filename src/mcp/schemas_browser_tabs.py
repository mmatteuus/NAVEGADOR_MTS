"""Módulo de Schemas para Abas e Páginas do Navegador (Browser Tabs MCP).

Define os esquemas JSON Schema das ferramentas de controle de ciclo de vida de abas,
navegação e captura de tela/acessibilidade no navegador via extensão Manifest V3.
"""

from __future__ import annotations

from typing import Any, Dict, List

BROWSER_TAB_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "browser_navigate",
        "description": "Solicita a navegação para uma URL na aba ativa ou especificada; o retorno não garante que o carregamento terminou.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL completa para navegação (ex: https://github.com)"},
                "tabId": {"type": "integer", "description": "ID opcional da aba. Se omitido, usa a aba ativa."},
                "active": {"type": "boolean", "default": False, "description": "Se True, traz a aba para o primeiro plano. Padrão: False para não atrapalhar o usuário."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Captura a árvore de acessibilidade semântica (ARIA) da página ativa para a IA.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tabId": {"type": "integer", "description": "ID opcional da aba. Se omitido, usa a aba ativa."}
            }
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Captura a imagem visual da aba ativa no navegador em formato Base64.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                "quality": {"type": "integer", "minimum": 1, "maximum": 100, "default": 90},
                "tabId": {"type": "integer", "description": "ID opcional da aba. Se omitido, usa a aba ativa."}
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
                "tabId": {"type": "integer", "description": "ID da aba alvo para ações 'switch' ou 'close'"},
                "focusWindow": {"type": "boolean", "default": False, "description": "Para a ação 'switch', se True traz a janela principal do sistema para o primeiro plano."}
            },
            "required": ["action"]
        }
    }
]

__all__ = ["BROWSER_TAB_TOOLS", "get_browser_tab_tools"]


def get_browser_tab_tools() -> List[Dict[str, Any]]:
    """Retorna uma cópia da lista de ferramentas de abas do navegador."""
    return [dict(tool) for tool in BROWSER_TAB_TOOLS]
