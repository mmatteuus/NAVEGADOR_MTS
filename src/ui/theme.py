"""Módulo de Tema e Estilização Windows 11 Fluent Design.

Responsabilidades:
- Definição da paleta de cores Fluent para temas escuro e claro.
- Configuração de tipografia Segoe UI Variable e raios de cantos arredondados.
- Aplicação defensiva de efeitos Mica/Acrílico no Windows 11 com fallback.
"""

from dataclasses import dataclass
import sys
from typing import Any
import customtkinter as ctk

try:
    import pywinstyles
    _PYWINSTYLES_AVAILABLE = True
except ImportError:
    _PYWINSTYLES_AVAILABLE = False


@dataclass(frozen=True)
class FluentPalette:
    """Paleta de cores alinhada às diretrizes do Windows 11 Fluent Design."""

    # Cores de fundo e cartões
    bg_dark: str = "#141416"
    bg_light: str = "#F3F3F5"
    card_dark: str = "#1E1E22"
    card_light: str = "#FFFFFF"
    card_border_dark: str = "#2B2B33"
    card_border_light: str = "#E5E5EB"

    # Cores de destaque e estados
    accent: str = "#0078D4"
    accent_hover: str = "#1084E3"
    accent_dark: str = "#4CC2FF"
    success: str = "#107C41"
    warning: str = "#D83B01"
    error: str = "#D13438"

    # Cores de texto
    text_dark: str = "#FFFFFF"
    text_light: str = "#1A1A1A"
    subtext_dark: str = "#9E9EA6"
    subtext_light: str = "#606066"

    # Tipografia e dimensões
    font_family: str = "Segoe UI Variable Display"
    font_family_body: str = "Segoe UI Variable Text"
    corner_radius: int = 12
    card_corner_radius: int = 10


PALETTE = FluentPalette()


def configure_app_theme(mode: str = "dark") -> None:
    """Configura o modo de aparência do CustomTkinter (dark, light ou system)."""
    selected_mode = mode.lower() if mode.lower() in ("dark", "light", "system") else "dark"
    ctk.set_appearance_mode(selected_mode)
    ctk.set_default_color_theme("blue")


def apply_mica_theme(window: Any, is_dark: bool = True) -> bool:
    """Aplica o efeito Mica ou Acrylic nativo na janela no Windows 11."""
    if sys.platform != "win32":
        return False

    if _PYWINSTYLES_AVAILABLE and hasattr(window, "winfo_id"):
        try:
            pywinstyles.apply_style(window, "mica")
            return True
        except Exception:
            pass

    try:
        import ctypes
        hwnd = window.winfo_id()
        backdrop_type = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 38, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type)
        )
        return True
    except Exception:
        return False


def get_status_color(status: str) -> str:
    """Mapeia o estado de um serviço para a respectiva cor visual de semáforo."""
    st = status.lower()
    if st in ("conectado", "ativo", "online", "autorizado", "ok"):
        return PALETTE.success
    if st in ("reconectando", "alerta", "degredado", "iniciando"):
        return PALETTE.warning
    return PALETTE.error
