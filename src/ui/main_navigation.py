"""Alternância dos painéis com suporte ao layout moderno de barra lateral."""
from .theme import PALETTE


def show_panel(window, selected: str) -> None:
    for name in ("dashboard", "settings", "windows"):
        panel = getattr(window, f"panel_{name}")
        button = getattr(window, "btn_nav_dash" if name == "dashboard" else f"btn_nav_{name}")
        panel.grid_forget()
        is_active = (name == selected)
        button.configure(
            fg_color=PALETTE.accent if is_active else "transparent",
            font=(PALETTE.font_family_body, 12, "bold" if is_active else "normal")
        )
        if is_active:
            if hasattr(panel, "refresh"):
                panel.refresh()
            panel.grid(row=0, column=1, sticky="nsew", padx=(6, 16), pady=16)
