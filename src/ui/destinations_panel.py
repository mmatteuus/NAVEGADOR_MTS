"""Destinos concedidos pelo usuário: programas e pastas por agente."""
from __future__ import annotations
import customtkinter as ctk
from .window_assignment_panel import WindowAssignmentPanel
from .folder_assignment_panel import FolderAssignmentPanel


class DestinationsPanel(ctk.CTkTabview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.add("Programas")
        self.add("Pastas e arquivos")
        self.windows = WindowAssignmentPanel(self.tab("Programas"))
        self.folders = FolderAssignmentPanel(self.tab("Pastas e arquivos"))
        self.windows.pack(fill="both", expand=True)
        self.folders.pack(fill="both", expand=True)

    def refresh(self):
        self.windows.refresh()
        self.folders.refresh()
