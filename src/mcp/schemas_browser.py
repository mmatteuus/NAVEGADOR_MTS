"""Módulo de Schemas das Ferramentas de Navegador (Browser MCP).

Define os esquemas formais JSON Schema para todas as ferramentas
de automação e inspeção web compatíveis com a extensão Manifest V3.
Reúne e reexporta os esquemas modularizados de abas e ações para compatibilidade total.
"""

from __future__ import annotations

from typing import Any, Dict, List
from .schemas_browser_tabs import BROWSER_TAB_TOOLS, get_browser_tab_tools
from .schemas_browser_actions import BROWSER_ACTION_TOOLS, get_browser_action_tools

# Lista unificada de esquemas formais das ferramentas do navegador
# Mantém a mesma composição e ordem exata para compatibilidade retroativa absoluta
BROWSER_TOOLS: List[Dict[str, Any]] = [
    BROWSER_TAB_TOOLS[0],    # browser_navigate
    BROWSER_ACTION_TOOLS[0], # browser_click
    BROWSER_ACTION_TOOLS[1], # browser_type
    BROWSER_TAB_TOOLS[1],    # browser_snapshot
    BROWSER_TAB_TOOLS[2],    # browser_screenshot
    BROWSER_TAB_TOOLS[3],    # browser_manage_tabs
    BROWSER_ACTION_TOOLS[2], # browser_evaluate_js
    BROWSER_ACTION_TOOLS[3], # browser_scroll
    BROWSER_ACTION_TOOLS[4], # browser_hover
    BROWSER_ACTION_TOOLS[5], # browser_press_key
]

__all__ = [
    "BROWSER_TOOLS",
    "get_browser_tools",
    "BROWSER_TAB_TOOLS",
    "get_browser_tab_tools",
    "BROWSER_ACTION_TOOLS",
    "get_browser_action_tools",
]


def get_browser_tools() -> List[Dict[str, Any]]:
    """Retorna uma cópia da lista completa de ferramentas do navegador disponíveis."""
    return [dict(tool) for tool in BROWSER_TOOLS]
