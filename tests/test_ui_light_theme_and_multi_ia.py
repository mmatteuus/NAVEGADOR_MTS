"""Testes de Alto Contraste do Tema Claro/Escuro, Multi-IA e Compatibilidade Universal Windows."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from src.ui.theme import PALETTE
from src.ui.ai_config_helpers import (
    AI_PROVIDERS,
    generate_ai_mcp_config,
    install_ai_config_auto,
    list_tunnel_profiles,
    save_tunnel_profile,
)
from src.ui.main_window import MainWindow


def _srgb_channel(hex_pair: str) -> float:
    c = int(hex_pair, 16) / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = _srgb_channel(h[0:2]), _srgb_channel(h[2:4]), _srgb_channel(h[4:6])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_dual_mode_palette_wcag_high_contrast() -> None:
    """Garante que todas as tuplas dual-mode têm alto contraste tanto no modo claro quanto no escuro."""
    dual_fields = (
        "bg_dual", "card_dual", "card_alt_dual", "border_dual",
        "text_dual", "subtext_dual", "muted_dual", "accent_dual",
        "accent_hover_dual", "accent_text_dual", "ghost_hover_dual",
        "success_dual", "warning_dual", "error_dual",
    )
    for attr in dual_fields:
        val = getattr(PALETTE, attr)
        assert isinstance(val, tuple) and len(val) == 2
        assert val[0].startswith("#") and val[1].startswith("#")

    # Modo Claro (índice 0): texto principal vs fundos >= 12.0 (WCAG AAA)
    assert _contrast_ratio(PALETTE.text_dual[0], PALETTE.bg_dual[0]) >= 12.0
    assert _contrast_ratio(PALETTE.text_dual[0], PALETTE.card_dual[0]) >= 12.0
    assert _contrast_ratio(PALETTE.subtext_dual[0], PALETTE.card_dual[0]) >= 7.0
    assert _contrast_ratio(PALETTE.accent_text_dual[0], PALETTE.card_dual[0]) >= 7.0

    # Modo Escuro (índice 1): texto principal vs fundos >= 12.0 (WCAG AAA)
    assert _contrast_ratio(PALETTE.text_dual[1], PALETTE.bg_dual[1]) >= 12.0
    assert _contrast_ratio(PALETTE.text_dual[1], PALETTE.card_dual[1]) >= 12.0
    assert _contrast_ratio(PALETTE.subtext_dual[1], PALETTE.card_dual[1]) >= 7.0
    assert _contrast_ratio(PALETTE.accent_text_dual[1], PALETTE.card_dual[1]) >= 6.5


def test_no_windows_11_restriction_in_ui_or_computer_schemas() -> None:
    """Verifica que não há menções restritivas a 'Windows 11' em src/ui/ ou schemas_computer.py."""
    root = Path(__file__).resolve().parents[1]
    targets = list((root / "src" / "ui").glob("*.py")) + [root / "src" / "mcp" / "schemas_computer.py"]
    offenders = [
        p.relative_to(root).as_posix()
        for p in targets
        if "Windows 11" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Strings 'Windows 11' encontradas em: {offenders}"
    assert PALETTE.font_family == "Segoe UI"
    assert PALETTE.font_family_body == "Segoe UI"


@pytest.mark.parametrize("provider", ["claude", "gemini", "opencode", "cursor", "codex", "chatgpt"])
def test_ai_config_helpers_generate_and_install_valid_configs(provider: str, tmp_path: Path) -> None:
    """Valida a geração e instalação automática de JSON MCP para Claude, Gemini, OpenCode, Cursor, Codex e ChatGPT."""
    assert provider in AI_PROVIDERS
    raw = generate_ai_mcp_config(provider)
    parsed = json.loads(raw)
    assert "mcpServers" in parsed
    srv = parsed["mcpServers"]["navegador-mts"]
    assert "command" in srv and isinstance(srv["args"], list)
    assert srv["env"]["BROWSER_MTS_AGENT_ID"] == AI_PROVIDERS[provider]["agent_id"]

    if provider == "opencode":
        assert "mcp" in parsed and "navegador-mts" in parsed["mcp"]

    dest = tmp_path / f"{provider}_config.json"
    ok, msg = install_ai_config_auto(provider, target_path=dest)
    assert ok is True and msg
    if provider != "chatgpt":
        saved = json.loads(dest.read_text(encoding="utf-8"))
        assert "navegador-mts" in saved["mcpServers"]


def test_multi_tunnel_profiles_persistence(monkeypatch, tmp_path: Path) -> None:
    """Valida o salvamento e listagem de perfis Multi-Túneis no tunnel.json."""
    from src.core import config
    monkeypatch.setattr(config, "current_config", SimpleNamespace(app_data_dir=tmp_path, tunnel_id=""))
    monkeypatch.delenv("BROWSER_MTS_TUNNEL_ID", raising=False)

    tid = "tunnel_" + "f" * 32
    profiles = save_tunnel_profile("Agente Principal", tid, "openai")
    assert any(p["name"] == "Agente Principal" and p["tunnel_id"] == tid for p in profiles)

    cf_profiles = save_tunnel_profile("Túnel Cloudflare", "https://mts.trycloudflare.com", "cloudflared")
    assert len(cf_profiles) == 2
    listed = list_tunnel_profiles()
    assert len(listed) >= 2


def test_main_window_light_theme_and_ai_panel_navigation(monkeypatch) -> None:
    """Valida a navegação para o painel Multi-IA e a alternância para o Tema Claro."""
    monkeypatch.setattr("src.ui.window_assignment_panel.list_windows", lambda: [])
    win = MainWindow()
    try:
        win.update_idletasks()
        assert "Windows 11" not in win.title()
        win.show_ai()
        win.update_idletasks()
        assert win.panel_ai.winfo_manager() == "grid"
        win.toggle_theme()
        win.update_idletasks()
        assert win._current_theme == "light"
        assert "Claro" in win.btn_theme_toggle.cget("text")
        win.toggle_theme()
        assert win._current_theme == "dark"
    finally:
        win.destroy()
