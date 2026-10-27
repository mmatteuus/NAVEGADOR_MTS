"""Módulo do Painel de Configurações (Settings Panel).

Responsabilidades: Gerenciamento de credenciais DPAPI, rede, nome do túnel e inicialização.
"""

from __future__ import annotations

from typing import Any, Optional
import customtkinter as ctk
from .theme import PALETTE
from .autostart import is_autostart_enabled, set_autostart_enabled
from .uninstaller_dialog import show_uninstall_dialog
from ..core.config import (
    current_config, get_tunnel_id, save_tunnel_id,
    get_tunnel_name, save_tunnel_name,
)
from ..core.tunnel_service import tunnel_service
from ..core.security import encrypt_dpapi, decrypt_dpapi, mask_credential
from ..core.credential_validation import is_runtime_credential

__all__ = ["SettingsPanel", "is_autostart_enabled", "set_autostart_enabled"]


class SettingsPanel(ctk.CTkFrame):
    """Painel gráfico de configurações do NAVEGADOR MTS com tema Dual-Mode."""

    def __init__(self, master, on_status_message: Optional[Any] = None, on_shutdown_app: Optional[Any] = None, **kwargs) -> None:
        super().__init__(master, corner_radius=PALETTE.corner_radius, fg_color="transparent", **kwargs)
        self.on_status_message, self.on_shutdown_app = on_status_message, on_shutdown_app
        self._raw_api_key: Optional[str] = None
        self._load_saved_credentials()
        self._setup_ui()

    def _load_saved_credentials(self) -> None:
        cred = current_config.credentials_file
        if cred.exists():
            try: self._raw_api_key = decrypt_dpapi(cred.read_text(encoding="utf-8").strip())
            except Exception: self._raw_api_key = None

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        ent_kw = dict(corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self._build_api_section(ent_kw)
        self._build_network_section(ent_kw)
        self._build_system_section()
        self._build_action_section()

    def _build_api_section(self, ent_kw: dict) -> None:
        sec = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        sec.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        ctk.CTkLabel(sec, text="🔑 Runtime API Key (OpenAI Secure Tunnel)", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=14, pady=(8, 2))
        self.entry_key = ctk.CTkEntry(sec, placeholder_text="Cole a nova chave sk-...", width=400, **ent_kw)
        self.entry_key.insert(0, mask_credential(self._raw_api_key))
        self.entry_key.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(sec, text="Protegido via DPAPI do Windows. Nunca exibida em texto puro.", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dual).pack(anchor="w", padx=14, pady=(0, 6))

    def _build_network_section(self, ent_kw: dict) -> None:
        sec = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        sec.grid(row=1, column=0, sticky="ew", padx=16, pady=4)
        ctk.CTkLabel(sec, text="🌐 Identificação do Agente e Túnel Seguro", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=14, pady=(8, 4))

        f_name = ctk.CTkFrame(sec, fg_color="transparent")
        f_name.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(f_name, text="Nome do Túnel / Agente:", width=160, anchor="w", text_color=PALETTE.text_dual).pack(side="left")
        self.entry_tunnel_name = ctk.CTkEntry(f_name, placeholder_text="Ex: Claude Desktop, Agente Suporte...", width=280, **ent_kw)
        self.entry_tunnel_name.insert(0, get_tunnel_name())
        self.entry_tunnel_name.pack(side="left")

        f_id = ctk.CTkFrame(sec, fg_color="transparent")
        f_id.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(f_id, text="ID do Túnel (tunnel_...):", width=160, anchor="w", text_color=PALETTE.text_dual).pack(side="left")
        self.entry_tunnel = ctk.CTkEntry(f_id, width=280, **ent_kw)
        self.entry_tunnel.insert(0, get_tunnel_id())
        self.entry_tunnel.pack(side="left")

        self.btn_toggle_tunnel = ctk.CTkButton(
            f_id, text="Ligar Túnel", width=120, height=28, corner_radius=8,
            command=self._on_click_toggle_tunnel, fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF",
        )
        self.btn_toggle_tunnel.pack(side="left", padx=(8, 0))
        self.update_tunnel_button()

        f_port = ctk.CTkFrame(sec, fg_color="transparent")
        f_port.pack(fill="x", padx=14, pady=(2, 6))
        ctk.CTkLabel(f_port, text="Porta WebSocket Local:", width=160, anchor="w", text_color=PALETTE.text_dual).pack(side="left")
        self.entry_port = ctk.CTkEntry(f_port, width=80, **ent_kw)
        self.entry_port.insert(0, str(current_config.port))
        self.entry_port.pack(side="left")

    def _build_system_section(self) -> None:
        sec = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        sec.grid(row=2, column=0, sticky="ew", padx=16, pady=4)
        ctk.CTkLabel(sec, text="⚙️ Inicialização do Sistema", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=14, pady=(8, 2))
        self.switch_autostart = ctk.CTkSwitch(sec, text="Iniciar silenciosamente com o Windows (Bandeja)", text_color=PALETTE.text_dual)
        if is_autostart_enabled(): self.switch_autostart.select()
        self.switch_autostart.pack(anchor="w", padx=14, pady=(2, 6))

    def _build_action_section(self) -> None:
        self.lbl_feedback = ctk.CTkLabel(self, text="", text_color=PALETTE.success_dual)
        self.lbl_feedback.grid(row=3, column=0, pady=1)

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.grid(row=4, column=0, pady=(1, 8))
        ctk.CTkButton(btn_box, text="💾 Salvar Configurações", width=165, height=32, corner_radius=8, fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF", command=self.save_settings).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="🗑️ Desinstalar da Máquina", fg_color=PALETTE.error_dual, hover_color="#991B1B", text_color="#FFFFFF", width=175, height=32, corner_radius=8, command=lambda: show_uninstall_dialog(self, on_shutdown=self.on_shutdown_app)).pack(side="left", padx=5)

    def save_settings(self) -> None:
        new_key = self.entry_key.get().strip()
        if is_runtime_credential(new_key):
            try:
                current_config.ensure_directories()
                current_config.credentials_file.write_text(encrypt_dpapi(new_key), encoding="utf-8")
                self._raw_api_key = new_key
                self.entry_key.delete(0, "end")
                self.entry_key.insert(0, mask_credential(new_key))
            except Exception as exc:
                self.lbl_feedback.configure(text=f"Erro ao proteger credencial: {exc}", text_color=PALETTE.error)
                return
        try:
            save_tunnel_id(self.entry_tunnel.get())
            if getattr(self, "entry_tunnel_name", None) is not None:
                save_tunnel_name(self.entry_tunnel_name.get())
        except ValueError as exc:
            self.lbl_feedback.configure(text=str(exc), text_color=PALETTE.error)
            return
        set_autostart_enabled(self.switch_autostart.get() == 1)
        self.lbl_feedback.configure(text="✅ Configurações salvas!", text_color=PALETTE.success)

    def _on_click_toggle_tunnel(self) -> None:
        if tunnel_service.is_active:
            tunnel_service.stop()
            self.lbl_feedback.configure(text="Túnel encerrado com sucesso.", text_color=PALETTE.success)
        else:
            self.save_settings()
            msg, col = ("Túnel iniciado! Verifique o status no Dashboard.", PALETTE.success) if tunnel_service.start() else (f"Erro ao iniciar túnel: {tunnel_service.last_error}", PALETTE.error)
            self.lbl_feedback.configure(text=msg, text_color=col)
        self.update_tunnel_button()

    def update_tunnel_button(self) -> None:
        active = tunnel_service.is_active
        txt, fg, hov = ("Desligar Túnel", PALETTE.error_dual, "#991B1B") if active else ("Ligar Túnel", PALETTE.accent_dual, PALETTE.accent_hover_dual)
        self.btn_toggle_tunnel.configure(text=txt, fg_color=fg, hover_color=hov, text_color="#FFFFFF")
