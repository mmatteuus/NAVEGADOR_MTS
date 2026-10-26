"""Painel humano para conceder uma pasta exclusiva a uma sessão com tema Dual-Mode."""

from __future__ import annotations

from tkinter import filedialog
import customtkinter as ctk
from ..computer.folder_assignments import folder_grants
from .agent_choices import refresh_choices, require_active
from .theme import PALETTE


class FolderAssignmentPanel(ctk.CTkFrame):
    """Concede e revoga pastas isoladas por sessão de agente com alto contraste."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._sessions = []
        self._display_to_sid = {}
        ctk.CTkLabel(self, text="📁 Pastas Exclusivas por Agente", font=(PALETTE.font_family, 15, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=12, pady=(10, 2))
        self.session = ctk.CTkComboBox(self, values=["(nenhuma sessão)"], corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.session.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(self, text="🔄 Atualizar agentes", fg_color="transparent", border_width=1, border_color=PALETTE.border_dual, text_color=PALETTE.text_dual, hover_color=PALETTE.ghost_hover_dual, command=self.refresh).pack(padx=12, pady=2)
        ctk.CTkButton(self, text="📂 Escolher pasta e atribuir", fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF", command=self.assign).pack(padx=12, pady=6)
        ctk.CTkButton(self, text="🚫 Revogar", fg_color=PALETTE.error_dual, hover_color="#991B1B", text_color="#FFFFFF", command=self.revoke).pack(padx=12, pady=6)
        self.status = ctk.CTkLabel(self, text="Nenhuma pasta atribuída", text_color=PALETTE.subtext_dual)
        self.status.pack(fill="x", padx=12, pady=6)
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
            grant = folder_grants.assign(sid, path)
            self.status.configure(text=f"Atribuída: {grant.root}", text_color=PALETTE.success_dual)
        except (ValueError, OSError) as exc:
            self.status.configure(text=str(exc), text_color=PALETTE.error_dual)

    def revoke(self) -> None:
        sid = self._display_to_sid.get(self.session.get(), "")
        if sid and not sid.startswith("("):
            folder_grants.revoke(sid)
            self.status.configure(text=f"Revogada: {sid}", text_color=PALETTE.subtext_dual)
