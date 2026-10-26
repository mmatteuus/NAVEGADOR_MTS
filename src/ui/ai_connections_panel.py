"""Painel de Conexão Multi-IA e Gerenciador Multi-Túneis do NAVEGADOR MTS."""

from __future__ import annotations

import customtkinter as ctk
from .theme import PALETTE
from .ai_config_helpers import (
    AI_PROVIDERS,
    generate_ai_mcp_config,
    install_ai_config_auto,
    list_tunnel_profiles,
    save_tunnel_profile,
)
from ..core.config import get_tunnel_display_label, save_tunnel_id, save_tunnel_name
from ..mcp.session_manager import session_manager


class AIConnectionsPanel(ctk.CTkFrame):
    """Painel moderno para gerenciar múltiplas IAs simultâneas e perfis de túneis."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=PALETTE.corner_radius, fg_color="transparent", **kwargs)
        self._profiles = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Cartão 1: Agentes Conectados Agora (Multi-IA)
        self.card_active = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        self.card_active.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        hdr1 = ctk.CTkFrame(self.card_active, fg_color="transparent")
        hdr1.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(hdr1, text="🤖 Agentes Conectados Agora (Multi-IA)", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(side="left")
        ctk.CTkButton(hdr1, text="🧹 Limpar", width=80, height=26, corner_radius=6, fg_color="transparent", border_width=1, border_color=PALETTE.border_dual, text_color=PALETTE.text_dual, hover_color=PALETTE.ghost_hover_dual, command=self.clear_inactive_sessions).pack(side="right", padx=4)
        ctk.CTkButton(hdr1, text="🔄 Atualizar", width=90, height=26, corner_radius=6, fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF", command=self.refresh).pack(side="right")
        self.lbl_active_agents = ctk.CTkLabel(self.card_active, text="Nenhum agente ativo no momento.", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dual, anchor="w")
        self.lbl_active_agents.pack(fill="x", padx=14, pady=(0, 10))

        # Cartão 2: Conectar Outras IAs em 1 Clique
        self.card_oneclick = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        self.card_oneclick.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(self.card_oneclick, text="⚡ Conectar Outras IAs em 1 Clique (Claude, Google Gemini, OpenCode, Cursor, Codex, ChatGPT)", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(self.card_oneclick, text="Clique no seu agente para copiar o JSON MCP e configurar automaticamente com sessão isolada:", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dual).pack(anchor="w", padx=14, pady=(0, 6))

        grid_btns = ctk.CTkFrame(self.card_oneclick, fg_color="transparent")
        grid_btns.pack(fill="x", padx=12, pady=(2, 6))
        for idx, (key, meta) in enumerate(AI_PROVIDERS.items()):
            grid_btns.grid_columnconfigure(idx % 3, weight=1)
            btn = ctk.CTkButton(
                grid_btns, text=f"⚡ {meta['label']}", height=30, corner_radius=8,
                fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF",
                font=(PALETTE.font_family_body, 11, "bold"), command=lambda k=key: self.connect_ai_provider(k)
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=4, pady=3, sticky="ew")

        self.lbl_ai_feedback = ctk.CTkLabel(self.card_oneclick, text="", font=(PALETTE.font_family_body, 11), text_color=PALETTE.success_dual)
        self.lbl_ai_feedback.pack(anchor="w", padx=14, pady=(2, 8))

        # Cartão 3: Gerenciador Multi-Túneis
        self.card_tunnels = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius, fg_color=PALETTE.card_dual, border_width=1, border_color=PALETTE.border_dual)
        self.card_tunnels.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        ctk.CTkLabel(self.card_tunnels, text="🌐 Gerenciador Multi-Túneis (OpenAI / Cloudflare cloudflared / Custom)", font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.text_dual).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_current_tunnel = ctk.CTkLabel(self.card_tunnels, text=f"Túnel Principal Ativo: {get_tunnel_display_label()}", font=(PALETTE.font_family_body, 11), text_color=PALETTE.accent_text_dual)
        self.lbl_current_tunnel.pack(anchor="w", padx=14, pady=(0, 4))

        row_prof = ctk.CTkFrame(self.card_tunnels, fg_color="transparent")
        row_prof.pack(fill="x", padx=14, pady=3)
        self.combo_profiles = ctk.CTkComboBox(row_prof, values=["(nenhum perfil)"], width=260, corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.combo_profiles.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row_prof, text="🚀 Alternar Perfil", width=130, height=28, corner_radius=8, fg_color=PALETTE.accent_dual, hover_color=PALETTE.accent_hover_dual, text_color="#FFFFFF", command=self.activate_selected_profile).pack(side="left")

        row_add = ctk.CTkFrame(self.card_tunnels, fg_color="transparent")
        row_add.pack(fill="x", padx=14, pady=(3, 10))
        self.entry_prof_name = ctk.CTkEntry(row_add, placeholder_text="Nome (ex: Agente 2)", width=140, corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.entry_prof_name.pack(side="left", padx=(0, 4))
        self.combo_provider = ctk.CTkComboBox(row_add, values=["openai", "cloudflared", "custom"], width=110, corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.combo_provider.set("openai")
        self.combo_provider.pack(side="left", padx=4)
        self.entry_prof_id = ctk.CTkEntry(row_add, placeholder_text="tunnel_... ou URL", width=210, corner_radius=8, fg_color=PALETTE.card_alt_dual, text_color=PALETTE.text_dual, border_color=PALETTE.border_dual)
        self.entry_prof_id.pack(side="left", padx=4)
        ctk.CTkButton(row_add, text="➕ Salvar", width=90, height=28, corner_radius=8, fg_color=PALETTE.success_dual, text_color="#FFFFFF", command=self.add_tunnel_profile).pack(side="left", padx=(4, 0))

    def connect_ai_provider(self, provider: str) -> None:
        cfg_json = generate_ai_mcp_config(provider)
        try:
            self.clipboard_clear()
            self.clipboard_append(cfg_json)
        except Exception:
            pass
        ok, msg = install_ai_config_auto(provider)
        color = PALETTE.success_dual if ok else PALETTE.warning_dual
        self.lbl_ai_feedback.configure(text=f"✅ {AI_PROVIDERS[provider]['label']}: JSON copiado! ({msg})", text_color=color)

    def clear_inactive_sessions(self) -> None:
        for sid in list(session_manager._sessions.keys()):
            sess = session_manager.get_session(sid)
            if sess and sess.status != "active":
                session_manager._sessions.pop(sid, None)
        self.refresh()

    def add_tunnel_profile(self) -> None:
        try:
            save_tunnel_profile(self.entry_prof_name.get(), self.entry_prof_id.get(), self.combo_provider.get())
            self.lbl_ai_feedback.configure(text="✅ Perfil de túnel salvo com sucesso!", text_color=PALETTE.success_dual)
            self.refresh()
        except ValueError as exc:
            self.lbl_ai_feedback.configure(text=f"⚠️ {exc}", text_color=PALETTE.error_dual)

    def activate_selected_profile(self) -> None:
        sel = self.combo_profiles.get()
        for p in self._profiles:
            label = f"{p.get('name')} [{p.get('provider')}]"
            if label == sel:
                save_tunnel_name(p.get("name", ""))
                if p.get("provider") == "openai" and p.get("tunnel_id"):
                    try: save_tunnel_id(p["tunnel_id"])
                    except ValueError: pass
                self.lbl_ai_feedback.configure(text=f"🚀 Perfil ativado: {p.get('name')}", text_color=PALETTE.success_dual)
                self.refresh()
                return

    def refresh(self) -> None:
        active_ids = session_manager.list_active_sessions()
        if active_ids:
            items = [f"{(session_manager.get_session(s).agent_id if session_manager.get_session(s) else '') or 'Agente'} ({s[:10]})" for s in active_ids]
            self.lbl_active_agents.configure(text=f"🟢 {len(active_ids)} ativa(s): " + " | ".join(items), text_color=PALETTE.success_dual)
        else:
            self.lbl_active_agents.configure(text="⚪ Nenhuma sessão ativa no momento (aguardando conexões MCP).", text_color=PALETTE.subtext_dual)
        self.lbl_current_tunnel.configure(text=f"Túnel Principal Ativo: {get_tunnel_display_label()}")
        self._profiles = list_tunnel_profiles()
        vals = [f"{p.get('name')} [{p.get('provider', 'openai')}]" for p in self._profiles] or ["(nenhum perfil)"]
        self.combo_profiles.configure(values=vals)
        self.combo_profiles.set(vals[0])
