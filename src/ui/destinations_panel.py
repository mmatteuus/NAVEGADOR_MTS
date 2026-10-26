"""Destinos concedidos pelo usuário: programas e pastas por agente."""

from __future__ import annotations

import customtkinter as ctk
from .theme import PALETTE
from .window_assignment_panel import WindowAssignmentPanel
from .folder_assignment_panel import FolderAssignmentPanel


class DestinationsPanel(ctk.CTkTabview):
    """Abas de atribuição de janelas e pastas para agentes com estilização Dual-Mode."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=PALETTE.card_dual,
            segmented_button_fg_color=PALETTE.card_alt_dual,
            segmented_button_selected_color=PALETTE.accent_dual,
            segmented_button_selected_hover_color=PALETTE.accent_hover_dual,
            segmented_button_unselected_color=PALETTE.card_alt_dual,
            segmented_button_unselected_hover_color=PALETTE.ghost_hover_dual,
            text_color="#FFFFFF",
            border_width=1,
            border_color=PALETTE.border_dual,
            **kwargs,
        )
        self.add("Programas")
        self.add("Pastas e arquivos")
        self.windows = WindowAssignmentPanel(self.tab("Programas"))
        self.folders = FolderAssignmentPanel(self.tab("Pastas e arquivos"))
        self.windows.pack(fill="both", expand=True)
        self.folders.pack(fill="both", expand=True)

    def refresh(self) -> None:
        self.windows.refresh()
        self.folders.refresh()
