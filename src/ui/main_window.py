"""Módulo da Janela Principal (Main Window).

Responsabilidades:
- Janela principal Fluent UI com suporte a efeito Mica e cantos arredondados.
- Alternância de abas entre Dashboard e Configurações e alternância de temas.
- Interceptação de fechamento para minimizar para a bandeja do sistema.
"""

from typing import Optional
import customtkinter as ctk
from .theme import PALETTE, apply_mica_theme, configure_app_theme
from .dashboard_panel import DashboardPanel
from .settings_panel import SettingsPanel


class MainWindow(ctk.CTk):
    """Janela principal do aplicativo BROWSER MTS no Windows 11."""

    def __init__(self, on_close_to_tray: Optional[any] = None, on_quit_app: Optional[any] = None) -> None:
        super().__init__()
        self.on_close_to_tray = on_close_to_tray
        self.on_quit_app = on_quit_app
        self.latest_update_info = None
        self._current_theme = "dark"
        self._setup_window()
        self._setup_layout()

    def _setup_window(self) -> None:
        """Define propriedades da janela, dimensões, título e efeito Mica."""
        self.title("BROWSER MTS & COMPUTER USE — Windows 11")
        self.geometry("820x660")
        self.minsize(760, 580)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = max(0, (sw - 820) // 2), max(0, (sh - 660) // 2)
        self.geometry(f"820x660+{x}+{y}")
        apply_mica_theme(self, is_dark=True)

    def _setup_layout(self) -> None:
        """Monta a barra superior de navegação e os painéis de conteúdo."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.nav_bar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color="transparent")
        self.nav_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        
        lbl_brand = ctk.CTkLabel(
            self.nav_bar, text="🌐 BROWSER MTS",
            font=(PALETTE.font_family, 15, "bold"), text_color=PALETTE.accent_dark
        )
        lbl_brand.pack(side="left", padx=(0, 20))

        self.btn_nav_dash = ctk.CTkButton(self.nav_bar, text="📊 Dashboard", width=110, height=30, command=self.show_dashboard, fg_color=PALETTE.accent)
        self.btn_nav_dash.pack(side="left", padx=4)

        self.btn_nav_settings = ctk.CTkButton(self.nav_bar, text="⚙️ Configurações", width=120, height=30, command=self.show_settings, fg_color="transparent", text_color=PALETTE.text_dark)
        self.btn_nav_settings.pack(side="left", padx=4)

        self.btn_theme_toggle = ctk.CTkButton(self.nav_bar, text="🌙 Modo Escuro", width=110, height=30, command=self.toggle_theme, fg_color="transparent", border_width=1)
        self.btn_theme_toggle.pack(side="right")

        self.btn_update = ctk.CTkButton(self.nav_bar, text="🔄 Atualizações", width=115, height=30, command=lambda: self.check_for_updates_ui(auto_open=True), fg_color="transparent", border_width=1)
        self.btn_update.pack(side="right", padx=(0, 6))

        self.panel_dashboard = DashboardPanel(self)
        self.panel_settings = SettingsPanel(self)
        self.panel_dashboard.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))

    def show_dashboard(self) -> None:
        """Exibe o painel de Dashboard e atualiza o destaque do botão."""
        self.panel_settings.grid_forget()
        self.panel_dashboard.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.btn_nav_dash.configure(fg_color=PALETTE.accent)
        self.btn_nav_settings.configure(fg_color="transparent")

    def show_settings(self) -> None:
        """Exibe o painel de Configurações e atualiza o destaque do botão."""
        self.panel_dashboard.grid_forget()
        self.panel_settings.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.btn_nav_settings.configure(fg_color=PALETTE.accent)
        self.btn_nav_dash.configure(fg_color="transparent")

    def toggle_theme(self) -> None:
        """Alterna dinamicamente entre tema Claro e Escuro."""
        if self._current_theme == "dark":
            self._current_theme = "light"
            configure_app_theme("light")
            self.btn_theme_toggle.configure(text="☀️ Modo Claro")
            apply_mica_theme(self, is_dark=False)
        else:
            self._current_theme = "dark"
            configure_app_theme("dark")
            self.btn_theme_toggle.configure(text="🌙 Modo Escuro")
            apply_mica_theme(self, is_dark=True)

    def hide_to_tray(self) -> None:
        """Oculta a janela principal minimizando silenciosamente para a bandeja."""
        self.withdraw()
        if self.on_close_to_tray:
            self.on_close_to_tray()

    def show_from_tray(self) -> None:
        """Restaura a visibilidade da janela trazendo-a para o primeiro plano."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def check_for_updates_ui(self, auto_open: bool = True) -> None:
        """Verifica novas versões na API de releases e abre o popup se houver novidade."""
        import threading
        from ..core.updater import check_for_updates
        from .update_dialog import UpdateDialog

        self.btn_update.configure(state="disabled", text="Verificando...")

        def _worker():
            info = check_for_updates()
            def _update_ui():
                self.btn_update.configure(state="normal")
                if info and info.is_newer:
                    self.latest_update_info = info
                    self.btn_update.configure(text=f"✨ Atualizar ({info.version})", fg_color=PALETTE.success)
                    if auto_open:
                        UpdateDialog(self, update_info=info, on_shutdown_for_update=self.on_quit_app)
                else:
                    self.btn_update.configure(text="✓ Atualizado", fg_color="transparent")
                    self.after(3000, lambda: self.btn_update.configure(text="🔄 Atualizações"))
            self.after(0, _update_ui)

        threading.Thread(target=_worker, daemon=True, name="UpdateCheckThread").start()
