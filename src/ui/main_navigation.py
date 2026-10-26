"""Alternância dos painéis da janela principal com estilização Dual-Mode."""

from __future__ import annotations

from .theme import PALETTE

_NAV_TARGETS = (
    ("dashboard", "panel_dashboard", "btn_nav_dash"),
    ("ai", "panel_ai", "btn_nav_ai"),
    ("windows", "panel_windows", "btn_nav_windows"),
    ("settings", "panel_settings", "btn_nav_settings"),
)


def show_panel(window, selected: str) -> None:
    """Exibe o painel selecionado e aplica cores de alto contraste nos botões de navegação."""
    for name, panel_attr, btn_attr in _NAV_TARGETS:
        panel = getattr(window, panel_attr, None)
        button = getattr(window, btn_attr, None)
        if panel is None or button is None:
            continue
        panel.grid_forget()
        is_active = name == selected
        if is_active:
            button.configure(
                fg_color=PALETTE.accent_dual,
                hover_color=PALETTE.accent_hover_dual,
                text_color="#FFFFFF",
                font=(PALETTE.font_family_body, 11, "bold"),
            )
            if hasattr(panel, "refresh"):
                panel.refresh()
            panel.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        else:
            button.configure(
                fg_color="transparent",
                hover_color=PALETTE.ghost_hover_dual,
                text_color=PALETTE.text_dual,
                font=(PALETTE.font_family_body, 11, "normal"),
            )
