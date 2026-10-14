"""Módulo de Diálogo para Conectar com Agentes de IA e Teste Visual do Mouse.

Permite ao usuário copiar a configuração JSON do Servidor MCP, copiar o prompt
pronto para colar em qualquer IA e testar visualmente a movimentação física do mouse.
"""

import json
import math
import sys
import threading
import time
import customtkinter as ctk
from .theme import PALETTE
from ..computer.safety_gate import safety_gate
from ..computer.mouse import move_mouse, get_cursor_position

MCP_PROMPT_TEMPLATE = (
    "Você é meu assistente de IA com acesso ao BROWSER MTS. "
    "O servidor MCP está ativo localmente em ws://127.0.0.1:3456. "
    "Você pode navegar na web, inspecionar elementos e interagir com o computador."
)

class MCPConnectDialog(ctk.CTkToplevel):
    """Janela modal para cópia de credenciais MCP e teste visual do mouse."""

    def __init__(self, master, port: int = 3456, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.port = port
        self.title("🤖 Conectar com Agente de IA - BROWSER MTS")
        self.geometry("540x510")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._setup_ui()

    def _get_mcp_config_json(self) -> str:
        """Gera a configuração formatada compatível com Claude Desktop, Cursor e outros."""
        exe_path = sys.executable if getattr(sys, "frozen", False) else "C:\\Users\\MATEUS\\AppData\\Local\\Programs\\BROWSER MTS\\BROWSER_MTS.exe"
        cfg = {"mcpServers": {"browser-mts": {"command": exe_path, "args": ["--stdio"]}}}
        return json.dumps(cfg, indent=2, ensure_ascii=False)

    def _setup_ui(self) -> None:
        """Constrói a interface visual com seções de cópia e botão de teste do mouse."""
        self.lbl_title = ctk.CTkLabel(self, text="🤖 Conectar com Agente de IA", font=(PALETTE.font_family, 16, "bold"))
        self.lbl_title.pack(anchor="w", padx=20, pady=(14, 2))
        desc = "Copie o ID do Túnel para o ChatGPT ou a configuração JSON para o Claude Desktop/Cursor."
        ctk.CTkLabel(self, text=desc, font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dark, wraplength=500).pack(anchor="w", padx=20, pady=(0, 8))

        # 1. Configuração ChatGPT (Aba Túnel)
        card_chatgpt = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_chatgpt.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_chatgpt, text="🟢 Para ChatGPT (Modal 'Adicionar servidor MCP'):", font=(PALETTE.font_family, 12, "bold"), text_color=PALETTE.success).pack(anchor="w", padx=12, pady=(6, 2))
        f_cg = ctk.CTkFrame(card_chatgpt, fg_color="transparent")
        f_cg.pack(fill="x", padx=12, pady=(2, 6))
        self.entry_tunnel = ctk.CTkEntry(f_cg, width=280)
        self.entry_tunnel.insert(0, "tunnel_6a7aea545c408191889cd114d4a99d9b")
        self.entry_tunnel.configure(state="readonly")
        self.entry_tunnel.pack(side="left", padx=(0, 6))
        ctk.CTkButton(f_cg, text="📋 Copiar ID", width=95, height=28, command=self._copy_tunnel_id).pack(side="left", padx=2)
        ctk.CTkButton(f_cg, text="🚀 Ligar Túnel", width=95, height=28, fg_color=PALETTE.accent, hover_color=PALETTE.accent_hover, command=self._start_tunnel_bg).pack(side="left", padx=2)

        # 2. Configuração MCP JSON (Claude Desktop / Cursor)
        card_mcp = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_mcp.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_mcp, text="📋 Para Claude Desktop / Cursor (JSON):", font=(PALETTE.font_family, 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        f_cl = ctk.CTkFrame(card_mcp, fg_color="transparent")
        f_cl.pack(fill="x", padx=12, pady=(2, 6))
        ctk.CTkButton(f_cl, text="📋 Copiar Bloco JSON", height=28, command=self._copy_mcp_json).pack(side="left", padx=(0, 6))
        ctk.CTkButton(f_cl, text="💬 Copiar Prompt IA", height=28, command=self._copy_prompt).pack(side="left")

        # 3. Teste Visual do Mouse
        card_test = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_test.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_test, text="🐭 Teste Visual do Mouse:", font=(PALETTE.font_family, 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        f_btn = ctk.CTkFrame(card_test, fg_color="transparent")
        f_btn.pack(fill="x", padx=12, pady=(2, 6))
        self.btn_test_mouse = ctk.CTkButton(f_btn, text="✨ Mover Mouse em Círculo", fg_color=PALETTE.accent, hover_color=PALETTE.accent_hover, command=self._start_mouse_demo)
        self.btn_test_mouse.pack(side="left", padx=(0, 8))
        self.lbl_feedback = ctk.CTkLabel(f_btn, text="", font=(PALETTE.font_family_body, 11), text_color=PALETTE.success)
        self.lbl_feedback.pack(side="left")

    def _copy_tunnel_id(self) -> None:
        """Copia o ID do Túnel para o ChatGPT."""
        self.clipboard_clear()
        self.clipboard_append("tunnel_6a7aea545c408191889cd114d4a99d9b")
        self.lbl_feedback.configure(text="✅ ID do Túnel copiado! Cole no ChatGPT.", text_color=PALETTE.success)

    def _start_tunnel_bg(self) -> None:
        """Inicia o processo do túnel da OpenAI em segundo plano."""
        import subprocess, os
        bat = os.path.abspath("LIGAR_TUNEL_CHATGPT.bat")
        if os.path.exists(bat):
            subprocess.Popen([bat], shell=True)
            self.lbl_feedback.configure(text="🚀 Túnel iniciado em segundo plano!", text_color=PALETTE.success)
        else:
            self.lbl_feedback.configure(text="Arquivo LIGAR_TUNEL_CHATGPT.bat não encontrado.", text_color=PALETTE.error)

    def _start_mouse_demo(self) -> None:
        """Inicia uma thread para movimentar visivelmente o cursor na tela."""
        if not safety_gate.is_authorized():
            self.lbl_feedback.configure(text="⚠️ Ative a trava de controle antes!", text_color=PALETTE.warning)
            return

        self.lbl_feedback.configure(text="Movendo mouse na tela...", text_color=PALETTE.accent_blue)
        threading.Thread(target=self._run_mouse_circle, daemon=True).start()

    def _run_mouse_circle(self) -> None:
        """Executa um desenho orbital suave com o mouse na tela física."""
        import ctypes
        user32 = ctypes.windll.user32
        cur_x, cur_y = get_cursor_position()
        radius = 120
        for deg in range(0, 360, 8):
            rad = math.radians(deg)
            x = int(cur_x + radius * math.cos(rad))
            y = int(cur_y + radius * math.sin(rad))
            user32.SetCursorPos(x, y)
            time.sleep(0.015)
        user32.SetCursorPos(cur_x, cur_y)
        self.after(0, lambda: self.lbl_feedback.configure(text="✅ Teste concluído!", text_color=PALETTE.success))

def show_mcp_dialog(master, port: int = 3456) -> None:
    """Função utilitária para exibir a janela de conexão com agentes de IA."""
    MCPConnectDialog(master, port=port)
