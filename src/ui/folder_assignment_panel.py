"""Painel humano para conceder uma pasta exclusiva a uma sessão."""
from __future__ import annotations

from tkinter import filedialog
import customtkinter as ctk
from ..computer.folder_assignments import folder_grants
from .agent_choices import refresh_choices, require_active

class FolderAssignmentPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs); self._sessions = []; self._display_to_sid = {}
        self.session = ctk.CTkComboBox(self, values=["(nenhuma sessão)"])
        self.session.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(self, text="Atualizar agentes", command=self.refresh).pack(padx=12, pady=2)
        ctk.CTkButton(self, text="Escolher pasta e atribuir", command=self.assign).pack(padx=12, pady=6)
        ctk.CTkButton(self, text="Revogar", command=self.revoke).pack(padx=12, pady=6)
        self.status = ctk.CTkLabel(self, text="Nenhuma pasta atribuída"); self.status.pack(fill="x", padx=12, pady=6)
        self.refresh()

    def refresh(self) -> None:
        self._display_to_sid = refresh_choices(self.session)

    def assign(self) -> None:
        sid = self._display_to_sid.get(self.session.get(), "")
        try:
            require_active(sid)
            path = filedialog.askdirectory(title="Pasta exclusiva do agente")
            if not path: return
            require_active(sid)
            grant = folder_grants.assign(sid, path); self.status.configure(text=f"Atribuída: {grant.root}")
        except (ValueError, OSError) as exc: self.status.configure(text=str(exc))

    def revoke(self) -> None:
        sid = self._display_to_sid.get(self.session.get(), "")
        if sid and not sid.startswith("("): folder_grants.revoke(sid); self.status.configure(text=f"Revogada: {sid}")
