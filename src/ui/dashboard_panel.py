"""Módulo do Painel Principal (Dashboard em Tempo Real).

Visualização de status, Trava de Segurança e console de logs sanitizados no padrão Windows 11.
"""

from __future__ import annotations
import time
from typing import Optional
import customtkinter as ctk
from .theme import PALETTE, get_status_color
from ..computer.safety_gate import safety_gate
from ..core.updater import APP_VERSION
from ..core.config import get_tunnel_display_label


class DashboardPanel(ctk.CTkFrame):
    """Painel de controle visual com métricas e status em tempo real."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=PALETTE.corner_radius, **kwargs)
        self._setup_ui()
        safety_gate.add_listener(self._on_safety_gate_change)

    def _setup_ui(self) -> None:
        self.grid_columnconfigure((0, 1), weight=1)

        # Cabeçalho do Dashboard
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 4))
        self.lbl_system_status = ctk.CTkLabel(
            self.header_frame, text="● SISTEMA OPERACIONAL & ONLINE",
            font=(PALETTE.font_family, 14, "bold"), text_color=PALETTE.success
        )
        self.lbl_system_status.pack(side="left")
        self.lbl_version = ctk.CTkLabel(self.header_frame, text=f"Versão {APP_VERSION}", text_color=PALETTE.subtext_dark, font=(PALETTE.font_family_body, 11))
        self.lbl_version.pack(side="right")

        # Cartão 1: Servidor MCP e Agente
        self.card_mcp = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, border_width=1, border_color=PALETTE.card_border_dark)
        self.card_mcp.grid(row=1, column=0, sticky="nsew", padx=(16, 6), pady=4)
        ctk.CTkLabel(self.card_mcp, text="🔌 Servidor MCP Local", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_mcp_status = ctk.CTkLabel(self.card_mcp, text="Status: Ativo (Porta 3456)", anchor="w", font=(PALETTE.font_family_body, 12))
        self.lbl_mcp_status.pack(anchor="w", padx=14, pady=1)
        self.lbl_mcp_tunnel = ctk.CTkLabel(self.card_mcp, text=f"Agente: {get_tunnel_display_label()}", anchor="w", text_color=PALETTE.subtext_dark, font=(PALETTE.font_family_body, 11))
        self.lbl_mcp_tunnel.pack(anchor="w", padx=14, pady=1)
        self.lbl_mcp_latency = ctk.CTkLabel(self.card_mcp, text="Latência: -- ms", anchor="w", font=(PALETTE.font_family_body, 11))
        self.lbl_mcp_latency.pack(anchor="w", padx=14, pady=(1, 10))

        # Cartão 2: Extensão do Navegador
        self.card_ext = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, border_width=1, border_color=PALETTE.card_border_dark)
        self.card_ext.grid(row=1, column=1, sticky="nsew", padx=(6, 16), pady=4)
        ctk.CTkLabel(self.card_ext, text="🌐 Extensão Chrome / Edge", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_ext_status = ctk.CTkLabel(self.card_ext, text="Status: Aguardando...", anchor="w", font=(PALETTE.font_family_body, 12))
        self.lbl_ext_status.pack(anchor="w", padx=14, pady=1)
        self.lbl_ext_tab = ctk.CTkLabel(self.card_ext, text="Aba Ativa: Nenhuma", anchor="w", text_color=PALETTE.subtext_dark, font=(PALETTE.font_family_body, 11))
        self.lbl_ext_tab.pack(anchor="w", padx=14, pady=1)
        self.lbl_ext_port = ctk.CTkLabel(self.card_ext, text="Ponte: ws://127.0.0.1:3456", anchor="w", font=(PALETTE.font_family_body, 11))
        self.lbl_ext_port.pack(anchor="w", padx=14, pady=(1, 10))

        # Cartão 3: Trava de Controle do Computador (Computer Use)
        self.card_safety = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, border_width=1, border_color=PALETTE.card_border_dark)
        self.card_safety.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
        ctk.CTkLabel(self.card_safety, text="🛡️ CONTROLE DO COMPUTADOR (COMPUTER USE)", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        self.switch_safety = ctk.CTkSwitch(
            self.card_safety, text="Permitir controle de mouse, teclado e tela",
            command=self._on_switch_toggled, font=(PALETTE.font_family_body, 12)
        )
        self.switch_safety.pack(anchor="w", padx=14, pady=3)
        self.lbl_safety_desc = ctk.CTkLabel(self.card_safety, text="Status: 🔴 Desautorizado pelo usuário", anchor="w", font=(PALETTE.font_family_body, 11))
        self.lbl_safety_desc.pack(anchor="w", padx=14, pady=1)
        ctk.CTkLabel(self.card_safety, text="🚨 Kill-Switch de Emergência: Pressione ESC 3x para interromper", text_color=PALETTE.warning, font=(PALETTE.font_family_body, 11)).pack(anchor="w", padx=14, pady=(1, 8))

        # Cartão 4: Console de Registro de Atividades em Tempo Real
        self.card_logs = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, border_width=1, border_color=PALETTE.card_border_dark)
        self.card_logs.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=16, pady=(4, 10))
        self.rowconfigure(3, weight=1)
        ctk.CTkLabel(self.card_logs, text="📋 Registro de Atividades em Tempo Real", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        self.txt_logs = ctk.CTkTextbox(self.card_logs, height=120, font=("Consolas", 11), wrap="char", border_width=1, border_color=PALETTE.card_border_dark)
        self.txt_logs.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.txt_logs.configure(state="disabled")

        btn_box = ctk.CTkFrame(self.card_logs, fg_color="transparent")
        btn_box.pack(anchor="e", padx=12, pady=(0, 6))
        ctk.CTkButton(btn_box, text="Limpar", width=65, height=24, corner_radius=6, command=self.clear_logs).pack(side="right", padx=3)
        ctk.CTkButton(btn_box, text="Copiar", width=65, height=24, corner_radius=6, command=self.copy_logs).pack(side="right")

    def _on_switch_toggled(self) -> None:
        if self.switch_safety.get() == 1: safety_gate.authorize()
        else: safety_gate.revoke("Desativado pelo usuário no painel")

    def _on_safety_gate_change(self, authorized: bool, reason: str) -> None:
        def _update():
            if authorized:
                self.switch_safety.select()
                self.lbl_safety_desc.configure(text="Status: 🟢 O Agente PODE interagir com o computador", text_color=PALETTE.success)
            else:
                self.switch_safety.deselect()
                self.lbl_safety_desc.configure(text=f"Status: 🔴 Desautorizado ({reason})", text_color=PALETTE.error)
            self.append_log(f"Trava de segurança: {'Autorizado' if authorized else 'Revogado'} ({reason})")
        self.after(0, _update)

    def update_mcp_status(self, status: str, latency_ms: Optional[float] = None, port: Optional[int] = None) -> None:
        color = get_status_color(status)
        port_txt = f" (Porta {port})" if port else ""
        self.lbl_mcp_status.configure(text=f"Status: {status}{port_txt}", text_color=color)
        self.lbl_mcp_tunnel.configure(text=f"Agente: {get_tunnel_display_label()}")
        if port: self.lbl_ext_port.configure(text=f"Ponte: ws://127.0.0.1:{port}")
        if latency_ms is not None: self.lbl_mcp_latency.configure(text=f"Latência: {latency_ms:.1f} ms")

    def update_extension_status(self, connected: bool, active_tab: str = "") -> None:
        if connected:
            self.lbl_ext_status.configure(text="Status: 🟢 Conectada", text_color=PALETTE.success)
            self.lbl_ext_tab.configure(text=f"Aba: {active_tab or 'Detectada'}")
        else:
            self.lbl_ext_status.configure(text="Status: 🔴 Desconectada", text_color=PALETTE.error)
            self.lbl_ext_tab.configure(text="Aba: Nenhuma")

    def append_log(self, text: str) -> None:
        stamp = time.strftime("[%H:%M:%S] ")
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"{stamp}{text}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def clear_logs(self) -> None:
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")

    def copy_logs(self) -> None:
        content = self.txt_logs.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
