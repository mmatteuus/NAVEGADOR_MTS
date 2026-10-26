"""
Módulo de Definições de Tipos e Estruturas Win32 para Computer Use.

Este arquivo centraliza as estruturas ctypes, uniões e constantes da API Win32
(User32 e Gdi32) necessárias para a emissão de comandos de mouse, teclado e tela.
Seguindo o padrão do Windows x64 e as diretrizes de modularidade estrita.
"""

import ctypes
from ctypes import wintypes
import typing

if not hasattr(ctypes, "windll"):
    class _MockWindll:
        def __getattr__(self, name: str) -> "_MockWindll":
            return self
        def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> int:
            return 0
    ctypes.windll = _MockWindll()  # type: ignore[attr-defined]

# ==============================================================================
# Constantes do Sistema Operacional Windows (User32 / DPI / SendInput)
# ==============================================================================

# Tipos de entrada para a API SendInput
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Flags para controle e movimentação de mouse (SendInput MOUSEINPUT)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

# Flags para controle de teclado (SendInput KEYBDINPUT)
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Métricas de tela virtual para suporte a múltiplos monitores (GetSystemMetrics)
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80

# Códigos de Teclas Virtuais (Virtual Keys - VK) frequentes
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_ESCAPE = 0x1B
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Tecla ALT
VK_LWIN = 0x5B  # Tecla Windows Esquerda
VK_RWIN = 0x5C  # Tecla Windows Direita
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_BACK = 0x08
VK_DELETE = 0x2E

# ==============================================================================
# Estruturas ctypes em conformidade com a arquitetura Win32 x64
# ==============================================================================

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class MOUSEINPUT(ctypes.Structure):
    """Estrutura MOUSEINPUT da Win32 API para coordenadas e cliques."""
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    """Estrutura KEYBDINPUT para eventos de teclas físicas ou caracteres Unicode."""
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    """Estrutura HARDWAREINPUT para mensagens de hardware legadas."""
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    """União que encapsula os tipos específicos de entrada."""
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    """Estrutura mestre enviada para a função SendInput da biblioteca user32.dll."""
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]
