"""Painel humano para atribuir uma janela existente a um agente."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import customtkinter as ctk

from ..computer.window_assignments import window_assignments, window_identity
from .agent_choices import refresh_choices, require_active

user32 = ctypes.windll.user32


def list_windows() -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _param):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        result.append((int(hwnd), buf.value))
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return result


class WindowAssignmentPanel(ctk.CTkFrame):
    """Concede/revoga uma janela por ação explícita do usuário."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._windows: list[tuple[int, str]] = []
        self._build_controls()
        self.refresh()

    def _build_controls(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Janelas para agentes", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, padx=14, pady=(14, 6), sticky="w"
        )
        self.sessions = ctk.CTkComboBox(self, values=["(nenhuma sessão)"])
        self.sessions.grid(row=1, column=0, padx=14, pady=5, sticky="ew")
        self.windows = ctk.CTkComboBox(self, values=["(atualizar janelas)"])
        self.windows.grid(row=2, column=0, padx=14, pady=5, sticky="ew")
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, padx=14, pady=5, sticky="e")
        ctk.CTkButton(buttons, text="Atualizar", width=95, command=self.refresh).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Atribuir", width=95, command=self.assign).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Revogar", width=95, command=self.release).pack(side="left", padx=4)
        self.status = ctk.CTkLabel(self, text="Nenhuma atribuição ativa", anchor="w")
        self.status.grid(row=4, column=0, padx=14, pady=(5, 14), sticky="ew")

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

    def _selected(self, widget, values):
        choice = widget.get()
        for value, label in values:
            if label == choice:
                return value
        return None

    def assign(self) -> None:
        sid = self._sessions.get(self.sessions.get(), "")
        hwnd = self._selected(self.windows, [(h, f"{t} [{h}]") for h, t in self._windows])
        if not sid or sid.startswith("(") or hwnd is None:
            self.status.configure(text="Selecione uma sessão e uma janela")
            return
        try:
            require_active(sid)
            if window_identity(hwnd) != self._identities.get(hwnd):
                raise ValueError("A janela mudou; atualize a lista antes de atribuir")
            item = window_assignments.assign(sid, hwnd)
            self.status.configure(text=f"Atribuída: {item.hwnd} → {item.session_id} (PID {item.pid})")
        except ValueError as exc:
            self.status.configure(text=str(exc))

    def release(self) -> None:
        sid = self._sessions.get(self.sessions.get(), "")
        if sid and not sid.startswith("("):
            window_assignments.release(sid)
            self.status.configure(text=f"Atribuição revogada: {sid}")
