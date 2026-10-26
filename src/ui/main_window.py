"""Janela principal redesenhada com barra lateral moderna no padrão Windows 11."""

from typing import Optional
import customtkinter as ctk
from .theme import PALETTE, apply_mica_theme, configure_app_theme
from .dashboard_panel import DashboardPanel
from .settings_panel import SettingsPanel
from .destinations_panel import DestinationsPanel
from .main_navigation import show_panel


class MainWindow(ctk.CTk):
    """Janela principal do aplicativo BROWSER MTS com layout de barra lateral moderna."""

    def __init__(self, on_close_to_tray: Optional[any] = None, on_quit_app: Optional[any] = None) -> None:
        super().__init__()
        self.on_close_to_tray, self.on_quit_app = on_close_to_tray, on_quit_app
        self.latest_update_info, self._update_timer = None, None
        self._update_dialog, self._update_check_in_flight, self._current_theme = None, False, "dark"
        self._setup_window()
        self._setup_layout()

    def _setup_window(self) -> None:
        self.title("NAVEGADOR MTS — Centro de Automação Windows 11")
        self.geometry("980x700")
        self.minsize(860, 620)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"980x700+{max(0, (sw - 980) // 2)}+{max(0, (sh - 700) // 2)}")
        apply_mica_theme(self, is_dark=True)

    def _setup_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Barra Lateral Esquerda (Sidebar Moderna)
        self.sidebar = ctk.CTkFrame(self, width=225, corner_radius=0, border_width=1, border_color=PALETTE.card_border_dark)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_propagate(False)

        # Topo da Sidebar
        f_brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_brand.pack(fill="x", padx=16, pady=(18, 14))
        ctk.CTkLabel(f_brand, text="🌐 NAVEGADOR MTS", font=(PALETTE.font_family, 15, "bold"), text_color=PALETTE.accent_dark).pack(anchor="w")
        ctk.CTkLabel(f_brand, text="Automação & IA para Windows", font=(PALETTE.font_family_body, 10), text_color=PALETTE.subtext_dark).pack(anchor="w")

        # Itens de Menu
        ctk.CTkLabel(self.sidebar, text="MENU PRINCIPAL", font=(PALETTE.font_family, 10, "bold"), text_color=PALETTE.subtext_dark).pack(anchor="w", padx=16, pady=(8, 4))
        self.btn_nav_dash = ctk.CTkButton(self.sidebar, text="  📊  Visão Geral", height=36, corner_radius=8, anchor="w", command=self.show_dashboard, fg_color=PALETTE.accent)
        self.btn_nav_dash.pack(fill="x", padx=12, pady=2)

        self.btn_nav_windows = ctk.CTkButton(self.sidebar, text="  🪟  Destinos & Janelas", height=36, corner_radius=8, anchor="w", command=self.show_windows, fg_color="transparent", text_color=PALETTE.text_dark)
        self.btn_nav_windows.pack(fill="x", padx=12, pady=2)

        self.btn_nav_settings = ctk.CTkButton(self.sidebar, text="  ⚙️  Configurações", height=36, corner_radius=8, anchor="w", command=self.show_settings, fg_color="transparent", text_color=PALETTE.text_dark)
        self.btn_nav_settings.pack(fill="x", padx=12, pady=2)

        ctk.CTkLabel(self.sidebar, text="INTEGRAÇÃO", font=(PALETTE.font_family, 10, "bold"), text_color=PALETTE.subtext_dark).pack(anchor="w", padx=16, pady=(14, 4))
        self.btn_mcp_connect = ctk.CTkButton(self.sidebar, text="  🤖  Conectar Agente IA", height=36, corner_radius=8, anchor="w", command=self.open_mcp_connect_dialog, fg_color=PALETTE.accent, hover_color=PALETTE.accent_hover)
        self.btn_mcp_connect.pack(fill="x", padx=12, pady=2)

        # Rodapé da Sidebar
        f_foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_foot.pack(side="bottom", fill="x", padx=12, pady=14)
        ctk.CTkLabel(f_foot, text="● Servidor Local Ativo (3456)", font=(PALETTE.font_family_body, 10), text_color=PALETTE.success).pack(anchor="w", pady=(0, 6))

        f_foot_btns = ctk.CTkFrame(f_foot, fg_color="transparent")
        f_foot_btns.pack(fill="x")
        self.btn_update = ctk.CTkButton(f_foot_btns, text="🔄 Atualizar", height=30, corner_radius=8, command=lambda: self.check_for_updates_ui(auto_open=True), fg_color="transparent", border_width=1, border_color=PALETTE.card_border_dark)
        self.btn_update.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.btn_theme_toggle = ctk.CTkButton(f_foot_btns, text="🌙", width=34, height=30, corner_radius=8, command=self.toggle_theme, fg_color="transparent", border_width=1, border_color=PALETTE.card_border_dark)
        self.btn_theme_toggle.pack(side="right")

        # Painéis Principais
        self.panel_dashboard = DashboardPanel(self)
        self.panel_settings = SettingsPanel(self, on_shutdown_app=self.on_quit_app)
        self.panel_windows = DestinationsPanel(self)
        self.show_dashboard()

    def open_mcp_connect_dialog(self) -> None:
        from .mcp_copy_dialog import show_mcp_dialog
        show_mcp_dialog(self)

    def show_dashboard(self) -> None:
        show_panel(self, "dashboard")

    def show_settings(self) -> None:
        show_panel(self, "settings")

    def show_windows(self) -> None:
        show_panel(self, "windows")

    def toggle_theme(self) -> None:
        is_dark = self._current_theme == "dark"
        self._current_theme = "light" if is_dark else "dark"
        configure_app_theme(self._current_theme)
        self.btn_theme_toggle.configure(text="☀️" if is_dark else "🌙")
        apply_mica_theme(self, is_dark=not is_dark)

    def hide_to_tray(self) -> None:
        self.withdraw()
        if self.on_close_to_tray: self.on_close_to_tray()

    def show_from_tray(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def check_for_updates_ui(self, auto_open: bool = True) -> None:
        import threading
        from ..core.updater import check_for_updates
        from .update_dialog import UpdateDialog
        if self._update_check_in_flight: return
        self._update_check_in_flight = True
        if self._update_timer: self.after_cancel(self._update_timer); self._update_timer = None
        self.btn_update.configure(state="disabled", text="Verificando...")

        def _worker():
            info = check_for_updates()
            def _update_ui():
                self._update_check_in_flight = False
                self._update_timer = self.after(3600000, lambda: self.check_for_updates_ui(auto_open=True))
                self.btn_update.configure(state="normal")
                if not info or info.status in ("error", "unavailable"):
                    self.btn_update.configure(text="⚠ Erro", fg_color=PALETTE.error)
                    self.after(5000, lambda: self.btn_update.configure(text="🔄 Atualizar", fg_color="transparent"))
                elif info.is_newer:
                    self.latest_update_info = info
                    self.btn_update.configure(text=f"✨ Atualizar ({info.version})", fg_color=PALETTE.success)
                    if auto_open and not (self._update_dialog and self._update_dialog.winfo_exists()):
                        self._update_dialog = UpdateDialog(self, update_info=info, on_shutdown_for_update=self.on_quit_app)
                else:
                    self.btn_update.configure(text="✓ Atualizado", fg_color="transparent")
                    self.after(3000, lambda: self.btn_update.configure(text="🔄 Atualizar"))
            self.after(0, _update_ui)
        threading.Thread(target=_worker, daemon=True, name="UpdateCheckThread").start()
