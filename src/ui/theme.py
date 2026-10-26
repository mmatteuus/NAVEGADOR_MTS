"""Módulo de Tema e Estilização Moderna Fluent Design para Windows.

Definição da paleta de cores Dual-Mode (Claro e Escuro) com alto contraste WCAG AAA,
tipografia universal Segoe UI e aplicação defensiva de tema DWM em qualquer Windows.
"""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any, Tuple
import customtkinter as ctk

try:
    import pywinstyles
    _PYWINSTYLES_AVAILABLE = True
except ImportError:
    _PYWINSTYLES_AVAILABLE = False

DualColor = Tuple[str, str]


@dataclass(frozen=True)
class FluentPalette:
    """Paleta de cores Dual-Mode e campos legados com contraste WCAG AAA."""

    # Campos legados (mantidos para compatibilidade retroativa)
    bg_dark: str = "#0F1117"
    bg_light: str = "#F1F5F9"
    card_dark: str = "#181B24"
    card_light: str = "#FFFFFF"
    card_border_dark: str = "#2E3646"
    card_border_light: str = "#CBD5E1"
    accent: str = "#005FB8"
    accent_hover: str = "#004C93"
    accent_dark: str = "#60A5FA"
    accent_light: str = "#004E8C"
    accent_blue: str = "#2563EB"
    success: str = "#107C41"
    warning: str = "#D83B01"
    error: str = "#D13438"
    text_dark: str = "#F8FAFC"
    text_light: str = "#0F172A"
    subtext_dark: str = "#CBD5E1"
    subtext_light: str = "#334155"

    # Tuplas Dual-Mode (cor_light, cor_dark) de alto contraste WCAG AAA
    bg_dual: DualColor = ("#F1F5F9", "#0F1117")
    card_dual: DualColor = ("#FFFFFF", "#181B24")
    card_alt_dual: DualColor = ("#F8FAFC", "#212634")
    border_dual: DualColor = ("#CBD5E1", "#2E3646")
    text_dual: DualColor = ("#0F172A", "#F8FAFC")
    subtext_dual: DualColor = ("#334155", "#CBD5E1")
    muted_dual: DualColor = ("#475569", "#94A3B8")
    accent_dual: DualColor = ("#005FB8", "#2563EB")
    accent_hover_dual: DualColor = ("#004C93", "#1D4ED8")
    accent_text_dual: DualColor = ("#004E8C", "#60A5FA")
    ghost_hover_dual: DualColor = ("#E2E8F0", "#262C3A")
    success_dual: DualColor = ("#047857", "#10B981")
    warning_dual: DualColor = ("#B45309", "#F59E0B")
    error_dual: DualColor = ("#B91C1C", "#EF4444")

    # Tipografia universal Windows e dimensões
    font_family: str = "Segoe UI"
    font_family_body: str = "Segoe UI"
    corner_radius: int = 12
    card_corner_radius: int = 10


PALETTE = FluentPalette()


def configure_app_theme(mode: str = "dark") -> None:
    """Configura o modo de aparência do CustomTkinter (dark, light ou system)."""
    selected_mode = mode.lower() if mode.lower() in ("dark", "light", "system") else "dark"
    ctk.set_appearance_mode(selected_mode)
    ctk.set_default_color_theme("blue")


def apply_mica_theme(window: Any, is_dark: bool = True) -> bool:
    """Aplica modo escuro/claro DWM em qualquer Windows e Mica quando is_dark=True."""
    if sys.platform != "win32":
        return False
    try:
        if hasattr(window, "configure"):
            window.configure(fg_color=PALETTE.bg_light if not is_dark else PALETTE.bg_dual)
    except Exception:
        pass
    if is_dark and _PYWINSTYLES_AVAILABLE and hasattr(window, "winfo_id"):
        try:
            pywinstyles.apply_style(window, "mica")
            return True
        except Exception:
            pass
    try:
        import ctypes
        hwnd = window.winfo_id()
        dwmapi = ctypes.windll.dwmapi
        dark_val = ctypes.c_int(1 if is_dark else 0)
        for attr in (20, 19):
            dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
        if is_dark:
            backdrop = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
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
