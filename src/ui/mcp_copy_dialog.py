"""Módulo de Diálogo para Conectar com Agentes de IA e Teste Visual do Mouse.

Permite ao usuário copiar a URL do Servidor (universal), o ID do Túnel OpenAI (ChatGPT),
a configuração JSON para Claude Desktop/Cursor e testar a movimentação do mouse.
"""

import json
import math
import sys
import threading
import time
import customtkinter as ctk
from .theme import PALETTE
from ..computer.safety_gate import safety_gate
from ..computer.mouse import get_cursor_position
from ..core.tunnel_service import tunnel_service, TUNNEL_ID

MCP_PROMPT_TEMPLATE = (
    "Você é meu assistente de IA com acesso ao Navegador MTS. "
    "O servidor MCP está ativo localmente em ws://127.0.0.1:3456. "
    "Você pode navegar na web, inspecionar elementos e interagir com o computador."
)


class MCPConnectDialog(ctk.CTkToplevel):
    """Janela modal para cópia de credenciais MCP e teste visual do mouse."""

    def __init__(self, master, port: int = 3456, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.port = port
        self.title("🤖 Conectar com Agente de IA - Navegador MTS")
        self.geometry("560x540")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._setup_ui()

    def _get_mcp_config_json(self) -> str:
        """Gera a configuração formatada compatível com Claude Desktop e Cursor."""
        exe = sys.executable
        args = ["--stdio"] if getattr(sys, "frozen", False) else ["-m", "src.app", "--stdio"]
        cfg = {"mcpServers": {"navegador-mts": {"command": exe, "args": args}}}
        return json.dumps(cfg, indent=2, ensure_ascii=False)

    def _setup_ui(self) -> None:
        """Constrói a interface com opções universais para todos os tipos de agentes."""
        ctk.CTkLabel(self, text="🤖 Conectar Agentes de IA ao Navegador MTS", font=(PALETTE.font_family, 15, "bold")).pack(anchor="w", padx=20, pady=(12, 2))
        ctk.CTkLabel(self, text="Escolha a forma mais conveniente para o seu agente ou ChatGPT:", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dark).pack(anchor="w", padx=20, pady=(0, 6))

        # 1. ChatGPT (Aba Túnel)
        card_t = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_t.pack(fill="x", padx=20, pady=4)
        status_txt = "🟢 Túnel Ativo no App" if tunnel_service.is_active else "🟡 Túnel em Segundo Plano"
        ctk.CTkLabel(card_t, text=f"1. ChatGPT (Aba 'Túnel') — {status_txt}", font=(PALETTE.font_family, 12, "bold"), text_color=PALETTE.success).pack(anchor="w", padx=12, pady=(6, 2))
        f_t = ctk.CTkFrame(card_t, fg_color="transparent")
        f_t.pack(fill="x", padx=12, pady=(2, 6))
        self.ent_tunnel = ctk.CTkEntry(f_t, width=300)
        self.ent_tunnel.insert(0, TUNNEL_ID)
        self.ent_tunnel.configure(state="readonly")
        self.ent_tunnel.pack(side="left", padx=(0, 6))
        ctk.CTkButton(f_t, text="📋 Copiar ID", width=95, height=28, command=self._copy_tunnel).pack(side="left", padx=2)
        ctk.CTkButton(f_t, text="🚀 Ligar Túnel", width=95, height=28, fg_color=PALETTE.accent, command=self._start_tunnel).pack(side="left", padx=2)

        # 2. Universal (Aba 'URL do Servidor' no ChatGPT e Outros Agentes)
        card_u = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_u.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_u, text="2. Qualquer Agente ou ChatGPT (Aba 'URL do Servidor'):", font=(PALETTE.font_family, 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        f_u = ctk.CTkFrame(card_u, fg_color="transparent")
        f_u.pack(fill="x", padx=12, pady=(2, 6))
        self.ent_url = ctk.CTkEntry(f_u, width=300)
        self.ent_url.insert(0, "URL pública MCP HTTPS exigida no ChatGPT")
        self.ent_url.configure(state="readonly")
        self.ent_url.pack(side="left", padx=(0, 6))
        ctk.CTkButton(f_u, text="📋 Copiar URL", width=95, height=28, command=self._copy_url).pack(side="left", padx=2)

        # 3. Claude Desktop / Cursor (Stdio JSON)
        card_j = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_j.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_j, text="3. Claude Desktop & Cursor (Stdio MCP):", font=(PALETTE.font_family, 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        f_j = ctk.CTkFrame(card_j, fg_color="transparent")
        f_j.pack(fill="x", padx=12, pady=(2, 6))
        ctk.CTkButton(f_j, text="📋 Copiar Bloco JSON", height=28, command=self._copy_json).pack(side="left", padx=(0, 6))

        # 4. Feedback e Teste Visual do Mouse
        card_m = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_m.pack(fill="x", padx=20, pady=4)
        f_m = ctk.CTkFrame(card_m, fg_color="transparent")
        f_m.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(f_m, text="🐭 Testar Movimento do Mouse", fg_color=PALETTE.accent, command=self._start_mouse_demo).pack(side="left", padx=(0, 8))
        self.lbl_feedback = ctk.CTkLabel(f_m, text="", font=(PALETTE.font_family_body, 11), text_color=PALETTE.success)
        self.lbl_feedback.pack(side="left")

    def _copy_tunnel(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(TUNNEL_ID)
        self.lbl_feedback.configure(text="✅ ID do Túnel copiado! Cole no ChatGPT.", text_color=PALETTE.success)

    def _copy_url(self) -> None:
        url = f"http://127.0.0.1:3457/mcp"
        self.clipboard_clear()
        self.clipboard_append(url)
        self.lbl_feedback.configure(text="Endpoint local: exige túnel HTTPS para ChatGPT.", text_color=PALETTE.warning)

    def _copy_json(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._get_mcp_config_json())
        self.lbl_feedback.configure(text="✅ Configuração JSON copiada!", text_color=PALETTE.success)

    def _start_tunnel(self) -> None:
        started = tunnel_service.start()
        if started:
            self.lbl_feedback.configure(text="🟢 Túnel iniciado com sucesso pelo aplicativo!", text_color=PALETTE.success)
        else:
            self.lbl_feedback.configure(text="⚠️ Não foi possível iniciar o túnel.", text_color=PALETTE.error)

    def _start_mouse_demo(self) -> None:
        if not safety_gate.is_authorized():
            self.lbl_feedback.configure(text="⚠️ Ative a trava de controle no painel!", text_color=PALETTE.warning)
            return
        self.lbl_feedback.configure(text="Movendo mouse...", text_color=PALETTE.accent_blue)
        threading.Thread(target=self._run_mouse_circle, daemon=True).start()

    def _run_mouse_circle(self) -> None:
        import ctypes
        user32 = ctypes.windll.user32
        cur_x, cur_y = get_cursor_position()
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            user32.SetCursorPos(int(cur_x + 100 * math.cos(rad)), int(cur_y + 100 * math.sin(rad)))
            time.sleep(0.015)
        user32.SetCursorPos(cur_x, cur_y)
        self.after(0, lambda: self.lbl_feedback.configure(text="✅ Teste de mouse concluído!", text_color=PALETTE.success))


def show_mcp_dialog(master, port: int = 3456) -> None:
    MCPConnectDialog(master, port=port)
