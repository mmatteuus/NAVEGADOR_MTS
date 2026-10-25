"""Alternância dos painéis sem sobreposição ou destaques antigos."""
from .theme import PALETTE


def show_panel(window, selected):
    for name in ("dashboard", "settings", "windows"):
        panel = getattr(window, f"panel_{name}")
        button = getattr(window, "btn_nav_dash" if name == "dashboard" else f"btn_nav_{name}")
        panel.grid_forget()
        button.configure(fg_color=PALETTE.accent if name == selected else "transparent")
        if name == selected:
            if hasattr(panel, "refresh"):
                panel.refresh()
            panel.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
