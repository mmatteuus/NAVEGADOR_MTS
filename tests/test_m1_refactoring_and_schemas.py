"""Testes de conformidade do Marco 1: Refatoração de LOC e expansão de Schemas MCP."""
from __future__ import annotations

from pathlib import Path
import pytest
from src.ui.autostart import is_autostart_enabled as autostart_query
from src.ui.autostart import set_autostart_enabled as autostart_set
from src.ui.settings_panel import is_autostart_enabled as sp_autostart_query
from src.ui.settings_panel import set_autostart_enabled as sp_autostart_set
from src.mcp.schemas_browser_tabs import BROWSER_TAB_TOOLS, get_browser_tab_tools
from src.mcp.schemas_browser_actions import BROWSER_ACTION_TOOLS, get_browser_action_tools
from src.mcp.schemas_browser import BROWSER_TOOLS, get_browser_tools
from src.mcp.schemas_computer import COMPUTER_TOOLS, get_computer_tools
from src.mcp.computer_dispatch import _plan


def test_autostart_module_and_reexport() -> None:
    """Garante que as funções de autostart funcionam e são reexportadas por settings_panel."""
    assert autostart_query is sp_autostart_query
    assert autostart_set is sp_autostart_set
    assert isinstance(autostart_query(), bool)


def test_schemas_browser_modularization() -> None:
    """Valida a separação coesa de schemas de navegador entre abas e ações."""
    tab_tools = get_browser_tab_tools()
    action_tools = get_browser_action_tools()
    all_tools = get_browser_tools()

    assert len(tab_tools) >= 4 and len(action_tools) >= 6
    assert len(all_tools) == len(tab_tools) + len(action_tools)

    tab_names = {t["name"] for t in tab_tools}
    action_names = {t["name"] for t in action_tools}
    assert {"browser_navigate", "browser_manage_tabs", "browser_screenshot"}.issubset(tab_names)
    assert {"browser_click", "browser_type", "browser_scroll", "browser_hover"}.issubset(action_names)


def test_schemas_computer_background_and_scroll() -> None:
    """Valida a inclusão dos parâmetros de background, hwnd e ação scroll."""
    tools = {t["name"]: t for t in get_computer_tools()}
    mouse_props = tools["computer_mouse_action"]["inputSchema"]["properties"]
    assert "scroll" in mouse_props["action"]["enum"] and "delta" in mouse_props
    assert mouse_props["background"]["default"] is True and "hwnd" in mouse_props

    kbd_props = tools["computer_keyboard_action"]["inputSchema"]["properties"]
    assert kbd_props["background"]["default"] is True and "hwnd" in kbd_props


def test_computer_dispatch_scroll_and_enrichment() -> None:
    """Valida o repasse de background (default True), hwnd e coordenadas no scroll."""
    scroll_p = _plan("computer_mouse_action", {"action": "scroll", "delta": -120, "x": 450, "y": 320})
    assert scroll_p[0][0] == "computer_mouse_scroll"
    assert scroll_p[0][1]["deltaY"] == -120 and scroll_p[0][1]["x"] == 450 and scroll_p[0][1]["y"] == 320
    assert scroll_p[0][1]["background"] is True

    # Scroll sem coordenadas não deve injetar x nem y
    scroll_plain = _plan("computer_mouse_action", {"action": "scroll", "delta": 60})
    assert "x" not in scroll_plain[0][1] and scroll_plain[0][1]["background"] is True

    # Mouse move e keyboard type com repasse de hwnd e background padrão
    move_p = _plan("computer_mouse_action", {"action": "move", "x": 10, "y": 20, "hwnd": 1234})
    assert move_p[0][1]["background"] is True and move_p[0][1]["hwnd"] == 1234
    type_p = _plan("computer_keyboard_action", {"action": "type", "text": "OK", "hwnd": 1234})
    assert type_p[0][1]["background"] is True and type_p[0][1]["hwnd"] == 1234


def test_codebase_loc_under_150() -> None:
    """Garante que nenhum arquivo (.py, .js, .mjs) em src/ e tests/ exceda 150 linhas físicas.

    A contagem utiliza splitlines() para considerar linhas físicas reais (incluindo
    linhas em branco e comentários), prevenindo falsas conformidades por ferramentas de shell.
    """
    root_dir = Path(__file__).resolve().parents[1]
    exts = {".py", ".js", ".mjs"}
    violations = [
        (p.relative_to(root_dir).as_posix(), len(p.read_text(encoding="utf-8", errors="ignore").splitlines()))
        for base in (root_dir / "src", root_dir / "tests")
        for p in base.rglob("*")
        if p.is_file() and p.suffix in exts and len(p.read_text(encoding="utf-8", errors="ignore").splitlines()) > 150
    ]
    assert not violations, f"Arquivos excedendo o limite de 150 linhas: {violations}"
