"""Módulo do Painel de Configurações (Settings Panel).

Responsabilidades:
- Gerenciamento seguro da Runtime API Key com criptografia DPAPI e máscara visual.
- Configuração de parâmetros de rede (porta WebSocket e identificador de túnel).
- Gerenciamento de inicialização automática com o Windows via Registro (HKCU\\Run).
"""

import sys
from typing import Optional
import customtkinter as ctk
from .theme import PALETTE
from ..core.config import current_config, get_tunnel_id, save_tunnel_id
from ..core.security import encrypt_dpapi, decrypt_dpapi, mask_credential

# Chave do Registro do Windows para inicialização automática
_REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_APP_NAME = "BrowserMTS"

def is_autostart_enabled() -> bool:
    """Verifica se o aplicativo está configurado para iniciar com o Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _REG_APP_NAME)
            return True
    except Exception:
        return False

def set_autostart_enabled(enabled: bool) -> bool:
    """Habilita ou desabilita a inicialização automática no Registro do Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}" --minimized'
                else:
                    cmd = f'"{sys.executable}" -m src.app --minimized'
                winreg.SetValueEx(key, _REG_APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, _REG_APP_NAME)
                except FileNotFoundError:
                    pass
            return True
    except Exception:
        return False

class SettingsPanel(ctk.CTkFrame):
    """Painel gráfico de configurações do BROWSER MTS."""

    def __init__(self, master, on_status_message: Optional[any] = None, on_shutdown_app: Optional[any] = None, **kwargs) -> None:
        super().__init__(master, corner_radius=PALETTE.corner_radius, **kwargs)
        self.on_status_message = on_status_message
        self.on_shutdown_app = on_shutdown_app
        self._raw_api_key: Optional[str] = None
        self._load_saved_credentials()
        self._setup_ui()

    def _load_saved_credentials(self) -> None:
        """Carrega a Runtime API Key descriptografando via DPAPI em repouso."""
        cred_file = current_config.credentials_file
        if cred_file.exists():
            try:
                enc_data = cred_file.read_text(encoding="utf-8").strip()
                self._raw_api_key = decrypt_dpapi(enc_data)
            except Exception:
                self._raw_api_key = None

    def _setup_ui(self) -> None:
        """Constrói a interface visual dos campos de configuração."""
        self.grid_columnconfigure(0, weight=1)

        # Seção 1: Credenciais de API
        sec_api = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        sec_api.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        ctk.CTkLabel(sec_api, text="🔑 Runtime API Key (OpenAI Secure Tunnel)", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        
        masked = mask_credential(self._raw_api_key)
        self.entry_key = ctk.CTkEntry(sec_api, placeholder_text="Cole a nova chave sk-...", width=400)
        self.entry_key.insert(0, masked)
        self.entry_key.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sec_api, text="Protegido via DPAPI do Windows. Nunca exibida em texto puro.", font=(PALETTE.font_family_body, 11), text_color=PALETTE.subtext_dark).pack(anchor="w", padx=12, pady=(0, 10))

        # Seção 2: Parâmetros de Rede
        sec_net = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        sec_net.grid(row=1, column=0, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(sec_net, text="🌐 Parâmetros de Rede e Portas", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        
        f_row = ctk.CTkFrame(sec_net, fg_color="transparent")
        f_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(f_row, text="Porta WebSocket:", width=140, anchor="w").pack(side="left")
        self.entry_port = ctk.CTkEntry(f_row, width=100)
        self.entry_port.insert(0, str(current_config.port))
        self.entry_port.pack(side="left")

        f_row2 = ctk.CTkFrame(sec_net, fg_color="transparent")
        f_row2.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(f_row2, text="ID do Túnel:", width=140, anchor="w").pack(side="left")
        self.entry_tunnel = ctk.CTkEntry(f_row2, width=320)
        self.entry_tunnel.insert(0, get_tunnel_id())
        self.entry_tunnel.pack(side="left")

        # Seção 3: Sistema e Inicialização
        sec_sys = ctk.CTkFrame(self, corner_radius=PALETTE.card_corner_radius)
        sec_sys.grid(row=2, column=0, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(sec_sys, text="⚙️ Inicialização do Sistema", font=(PALETTE.font_family, 13, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        
        self.switch_autostart = ctk.CTkSwitch(sec_sys, text="Iniciar silenciosamente com o Windows (Bandeja)")
        if is_autostart_enabled():
            self.switch_autostart.select()
        self.switch_autostart.pack(anchor="w", padx=12, pady=(4, 10))

        # Botões de Ação
        self.lbl_feedback = ctk.CTkLabel(self, text="", text_color=PALETTE.success)
        self.lbl_feedback.grid(row=3, column=0, pady=(2, 2))
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.grid(row=4, column=0, pady=(2, 10))
        ctk.CTkButton(btn_box, text="💾 Salvar Configurações", width=170, height=32, command=self.save_settings).pack(side="left", padx=6)
        ctk.CTkButton(btn_box, text="🗑️ Desinstalar da Máquina", fg_color=PALETTE.error, hover_color="#A80000", width=190, height=32, command=self._on_click_uninstall).pack(side="left", padx=6)

    def _on_click_uninstall(self) -> None:
        """Abre diálogo para desinstalar o BROWSER MTS desta máquina."""
        from .uninstaller_dialog import show_uninstall_dialog
        show_uninstall_dialog(self, on_shutdown=self.on_shutdown_app)

    def save_settings(self) -> None:
        """Salva as configurações alteradas pelo usuário com proteção criptográfica."""
        new_key = self.entry_key.get().strip()
        if new_key and not new_key.startswith("•") and not new_key.startswith("sk-••"):
            try:
                enc_b64 = encrypt_dpapi(new_key)
                current_config.ensure_directories()
                current_config.credentials_file.write_text(enc_b64, encoding="utf-8")
                self._raw_api_key = new_key
                self.entry_key.delete(0, "end")
                self.entry_key.insert(0, mask_credential(new_key))
            except Exception as exc:
                self.lbl_feedback.configure(text=f"Erro ao proteger credencial: {exc}", text_color=PALETTE.error)
                return

        try:
            save_tunnel_id(self.entry_tunnel.get())
        except ValueError as exc:
            self.lbl_feedback.configure(text=str(exc), text_color=PALETTE.error)
            return
        set_autostart_enabled(self.switch_autostart.get() == 1)
        self.lbl_feedback.configure(text="✅ Configurações salvas com sucesso!", text_color=PALETTE.success)
