"""Diálogo Modal de Confirmação de Desinstalação do BROWSER MTS.

Responsabilidades:
- Exibição de aviso com opção de confirmação ou cancelamento da desinstalação.
- Acionamento do fluxo de encerramento do app e inicialização do desinstalador.
"""

from typing import Callable, Optional
import customtkinter as ctk
from .theme import PALETTE, apply_mica_theme
from ..core.uninstaller import trigger_application_uninstall


class UninstallDialog(ctk.CTkToplevel):
    """Janela popup de confirmação para desinstalar o BROWSER MTS."""

    def __init__(
        self,
        master,
        on_shutdown: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_shutdown = on_shutdown
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        """Define dimensões e centralização do diálogo de desinstalação."""
        self.title("Desinstalar Aplicativo — BROWSER MTS")
        self.geometry("480x280")
        self.resizable(False, False)
        self.transient(self.master)
        self.grab_set()

        self.update_idletasks()
        mx = self.master.winfo_x() + (self.master.winfo_width() - 480) // 2
        my = self.master.winfo_y() + (self.master.winfo_height() - 280) // 2
        self.geometry(f"480x280+{max(0, mx)}+{max(0, my)}")
        apply_mica_theme(self, is_dark=True)

    def _build_ui(self) -> None:
        """Monta os componentes visuais do diálogo de confirmação."""
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 10))
        ctk.CTkLabel(hdr, text="⚠️ Desinstalar BROWSER MTS?", font=(PALETTE.font_family, 16, "bold"), text_color=PALETTE.error).pack(anchor="w")

        body = ctk.CTkLabel(
            self,
            text="Tem certeza que deseja remover o BROWSER MTS desta máquina?\n\n"
                 "• O aplicativo será encerrado.\n"
                 "• Os atalhos da Área de Trabalho e do Menu Iniciar serão removidos.\n"
                 "• O assistente de desinstalação do Windows será iniciado.",
            font=(PALETTE.font_family_body, 12),
            justify="left",
            wraplength=430,
        )
        body.pack(fill="x", padx=24, pady=10)

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=(16, 20))

        ctk.CTkButton(
            btn_box, text="Cancelar", width=120, fg_color="transparent", border_width=1,
            command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_box, text="🗑️ Sim, Desinstalar", width=160, fg_color=PALETTE.error, hover_color="#A80000",
            command=self._confirm_uninstall
        ).pack(side="right")

    def _confirm_uninstall(self) -> None:
        """Dispara a desinstalação e fecha o diálogo."""
        self.destroy()
        trigger_application_uninstall(self.on_shutdown)


def show_uninstall_dialog(master, on_shutdown: Optional[Callable[[], None]] = None) -> None:
    """Função utilitária para exibir o diálogo modal de desinstalação."""
    UninstallDialog(master, on_shutdown=on_shutdown)

