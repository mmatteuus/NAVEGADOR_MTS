"""Painel humano para atribuir uma janela a um agente com controle granular de mouse e teclado."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import customtkinter as ctk

from ..computer.window_assignments import window_assignments, window_identity
from .agent_choices import refresh_choices, require_active
from .theme import PALETTE

user32 = ctypes.windll.user32


def list_windows() -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(
        lambda h, _: (
            result.append((int(h), b.value)) if user32.IsWindowVisible(h) and (l := user32.GetWindowTextLengthW(h)) and not user32.GetWindowTextW(h, (b := ctypes.create_unicode_buffer(l + 1)), l + 1) == 0 else True, True
        )[1]
    )
    user32.EnumWindows(cb, 0)
    return result


class WindowAssignmentPanel(ctk.CTkFrame):
    """Concede e revoga janelas e dispositivos (mouse/teclado) com alto contraste Dual-Mode."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._windows: list[tuple[int, str]] = []
        self._build_controls()
        self.refresh()

    def _build_controls(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="🎯 Janelas para Agentes de IA", font=(PALETTE.font_family, 15, "bold"), text_color=PALETTE.text_dual).grid(
            row=0, column=0, padx=16, pady=(12, 2), sticky="w"
        )
        ctk.CTkLabel(self, text="Vincule janelas aos agentes e selecione quais dispositivos permitir.", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dual).grid(
            row=1, column=0, padx=16, pady=(0, 6), sticky="w"
        )

        combo_kw = dict(corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.sessions = ctk.CTkComboBox(self, values=["(nenhuma sessão)"], **combo_kw)
        self.sessions.grid(row=2, column=0, padx=16, pady=3, sticky="ew")
        self.windows = ctk.CTkComboBox(self, values=["(atualizar janelas)"], **combo_kw)
        self.windows.grid(row=3, column=0, padx=16, pady=3, sticky="ew")

        f_checks = ctk.CTkFrame(self, fg_color="transparent")
        f_checks.grid(row=4, column=0, padx=16, pady=6, sticky="w")
        chk_kw = dict(font=(PALETTE.font_family_body, 12), corner_radius=6, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.chk_mouse = ctk.CTkCheckBox(f_checks, text="🖱️ Permitir Mouse", **chk_kw)
        self.chk_mouse.select()
        self.chk_mouse.pack(side="left", padx=(0, 16))

        self.chk_keyboard = ctk.CTkCheckBox(f_checks, text="⌨️ Permitir Teclado", **chk_kw)
        self.chk_keyboard.select()
        self.chk_keyboard.pack(side="left", padx=(0, 16))

        self.chk_focus = ctk.CTkCheckBox(f_checks, text="🔍 Permitir Foco", **chk_kw)
        self.chk_focus.pack(side="left")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=5, column=0, padx=16, pady=6, sticky="w")
        ctk.CTkButton(buttons, text="🔄 Atualizar", width=100, height=30, corner_radius=8, fg_color="transparent", border_width=1, border_color=PALETTE.border_dual, text_color=PALETTE.text_dual, hover_color=PALETTE.ghost_hover_dual, command=self.refresh).pack(side="left", padx=(0, 6))
        ctk.CTkButton(buttons, text="✅ Atribuir Janela", fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF", width=135, height=30, corner_radius=8, command=self.assign).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="🚫 Revogar", fg_color=PALETTE.error_dual, hover_color="#991B1B", text_color="#FFFFFF", width=95, height=30, corner_radius=8, command=self.release).pack(side="left", padx=6)

        self.card_status = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_alt_dual, border_width=1, border_color=PALETTE.border_dual)
        self.card_status.grid(row=6, column=0, padx=16, pady=(8, 12), sticky="ew")
        self.lbl_status = ctk.CTkLabel(self.card_status, text="Status: Nenhuma atribuição ativa", font=(PALETTE.font_family_body, 12), text_color=PALETTE.text_dual, anchor="w")
        self.lbl_status.pack(anchor="w", padx=14, pady=8)

    def refresh(self) -> None:
        self._windows = list_windows()
        self._identities = {}
        for hwnd, _title in self._windows:
            try: self._identities[hwnd] = window_identity(hwnd)
            except ValueError: pass
        values = [f"{title} [{hwnd}]" for hwnd, title in self._windows if hwnd in self._identities]
        previous = self.windows.get()
        self.windows.configure(values=values or ["(nenhuma janela)"], state="readonly")
        self.windows.set(previous if previous in values else "(selecione uma janela)")
        self._sessions = refresh_choices(self.sessions)
        self._update_current_status()

    def _selected(self, widget, values):
        choice = widget.get()
        for value, label in values:
            if label == choice: return value
        return None

    def _update_current_status(self) -> None:
        sid = self._sessions.get(self.sessions.get(), "")
        if sid and not sid.startswith("("):
            current = window_assignments.get(sid)
            if current:
                m_txt = "SIM" if current.allow_mouse else "NÃO"
                k_txt = "SIM" if current.allow_keyboard else "NÃO"
                self.lbl_status.configure(text=f"Ativa: HWND {current.hwnd} (PID {current.pid}) | 🖱️ Mouse: {m_txt} | ⌨️ Teclado: {k_txt}", text_color=PALETTE.text_dual)
                return
        self.lbl_status.configure(text="Status: Nenhuma janela atribuída para a sessão selecionada.", text_color=PALETTE.subtext_dual)

    def assign(self) -> None:
        sid = self._sessions.get(self.sessions.get(), "")
        hwnd = self._selected(self.windows, [(h, f"{t} [{h}]") for h, t in self._windows])
        if not sid or sid.startswith("(") or hwnd is None:
            self.lbl_status.configure(text="Selecione uma sessão e uma janela para atribuir.", text_color=PALETTE.warning_dual)
            return
        try:
            require_active(sid)
            if window_identity(hwnd) != self._identities.get(hwnd):
                raise ValueError("A janela mudou; atualize a lista antes de atribuir.")
            allow_m = self.chk_mouse.get() == 1
            allow_k = self.chk_keyboard.get() == 1
            allow_f = self.chk_focus.get() == 1
            item = window_assignments.assign(sid, hwnd, allow_focus=allow_f, allow_mouse=allow_m, allow_keyboard=allow_k)
            m_str = "Mouse: ON" if allow_m else "Mouse: OFF"
            k_str = "Teclado: ON" if allow_k else "Teclado: OFF"
            self.lbl_status.configure(text=f"✅ Atribuída com sucesso: {item.hwnd} → {item.session_id} ({m_str}, {k_str})", text_color=PALETTE.success_dual)
        except ValueError as exc:
            self.lbl_status.configure(text=str(exc), text_color=PALETTE.error_dual)

    def release(self) -> None:
        sid = self._sessions.get(self.sessions.get(), "")
        if sid and not sid.startswith("("):
            window_assignments.release(sid)
            self.lbl_status.configure(text=f"🚫 Atribuição revogada para a sessão: {sid}", text_color=PALETTE.subtext_dual)
