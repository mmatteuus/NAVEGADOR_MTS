"""Janela Popup de Notificação e Download de Atualizações do BROWSER MTS.

Responsabilidades:
- Exibição de diálogo modal Windows 11 com notas de lançamento e nova versão.
- Download assíncrono com barra de progresso em tempo real.
- Acionamento seguro do instalador in-place e encerramento limpo da sessão atual.
"""

import threading
from typing import Callable, Optional
import customtkinter as ctk
from .theme import PALETTE, apply_mica_theme
from ..core.updater import APP_VERSION, UpdateInfo, download_and_launch_update


class UpdateDialog(ctk.CTkToplevel):
    """Janela popup moderna para download e aplicação de atualizações."""

    def __init__(
        self,
        master,
        update_info: UpdateInfo,
        on_shutdown_for_update: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, **kwargs)
        self.update_info = update_info
        self.on_shutdown_for_update = on_shutdown_for_update
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        """Configurações de dimensões, centralização e estilo visual da janela popup."""
        self.title("Atualização Disponível — Navegador MTS")
        self.geometry("520x460")
        self.resizable(False, False)
        self.transient(self.master)
        self.grab_set()

        # Centraliza o popup em relação à janela principal
        self.update_idletasks()
        mx = self.master.winfo_x() + (self.master.winfo_width() - 520) // 2
        my = self.master.winfo_y() + (self.master.winfo_height() - 460) // 2
        self.geometry(f"520x460+{max(0, mx)}+{max(0, my)}")
        apply_mica_theme(self, is_dark=True)

    def _build_ui(self) -> None:
        """Monta os componentes gráficos do diálogo de atualização."""
        # Cabeçalho com ícone e chamada
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(hdr, text="🚀 Nova Versão Disponível!", font=(PALETTE.font_family, 17, "bold"), text_color=PALETTE.accent_dark).pack(anchor="w")
        
        # Cartão de Versões
        card_v = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        card_v.pack(fill="x", padx=20, pady=6)
        v_text = f"Versão Atual: v{APP_VERSION}   ➔   Nova Versão: {self.update_info.version}"
        ctk.CTkLabel(card_v, text=v_text, font=(PALETTE.font_family, 13, "bold"), text_color=PALETTE.success).pack(padx=14, pady=10)

        # Caixa com Notas de Lançamento (Changelog)
        ctk.CTkLabel(self, text="O que há de novo nesta versão:", font=(PALETTE.font_family, 12, "bold")).pack(anchor="w", padx=20, pady=(6, 2))
        self.txt_notes = ctk.CTkTextbox(self, height=140, font=("Segoe UI", 11), wrap="word")
        self.txt_notes.pack(fill="x", padx=20, pady=4)
        self.txt_notes.insert("1.0", self.update_info.release_notes or "Melhorias de estabilidade e novas ferramentas.")
        self.txt_notes.configure(state="disabled")

        # Barra de Progresso e Status
        self.lbl_status = ctk.CTkLabel(self, text="Clique em 'Atualizar Agora' para baixar e aplicar.", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dark)
        self.lbl_status.pack(anchor="w", padx=20, pady=(10, 2))
        self.prog_bar = ctk.CTkProgressBar(self, height=8)
        self.prog_bar.pack(fill="x", padx=20, pady=(2, 12))
        self.prog_bar.set(0.0)

        # Botões de Ação
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(6, 16))
        self.btn_cancel = ctk.CTkButton(btn_box, text="Lembrar Mais Tarde", fg_color="transparent", border_width=1, width=140, command=self.destroy)
        self.btn_cancel.pack(side="left")
        self.btn_apply = ctk.CTkButton(btn_box, text="⬇️ Atualizar Agora", fg_color=PALETTE.success, hover_color="#0E6B37", width=160, command=self._start_download)
        self.btn_apply.pack(side="right")

    def _start_download(self) -> None:
        """Inicia o download da atualização em thread de segundo plano."""
        self.btn_apply.configure(state="disabled", text="Baixando...")
        self.btn_cancel.configure(state="disabled")
        self.lbl_status.configure(text="Conectando aos servidores de atualização...", text_color=PALETTE.accent_dark)

        def _worker():
            def _progress(ratio: float):
                self.after(0, lambda: self._update_progress_ui(ratio))

            def _ready():
                self.after(0, self._on_ready_to_switch)

            success = download_and_launch_update(
                self.update_info,
                progress_callback=_progress,
                on_ready_to_install=_ready,
            )
            if not success:
                self.after(0, self._on_download_failed)

        threading.Thread(target=_worker, daemon=True, name="UpdateDownloadThread").start()

    def _update_progress_ui(self, ratio: float) -> None:
        """Atualiza a barra e o rótulo de progresso."""
        self.prog_bar.set(ratio)
        pct = int(ratio * 100)
        self.lbl_status.configure(text=f"Baixando nova versão: {pct}% concluído...", text_color=PALETTE.accent_dark)

    def _on_ready_to_switch(self) -> None:
        """Chamado quando o download termina e o instalador está pronto."""
        self.lbl_status.configure(text="Download concluído! Iniciando instalador...", text_color=PALETTE.success)
        if self.on_shutdown_for_update:
            self.after(1000, self.on_shutdown_for_update)

    def _on_download_failed(self) -> None:
        """Exibe mensagem de erro caso o download falhe."""
        self.lbl_status.configure(text="Falha no download da atualização. Tente novamente mais tarde.", text_color=PALETTE.error)
        self.btn_apply.configure(state="normal", text="Tentar Novamente")
        self.btn_cancel.configure(state="normal")

