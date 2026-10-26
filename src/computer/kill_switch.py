"""
Módulo de Kill-Switch de Emergência para Windows (3x ESC em < 1.2s).

Captura globalmente a tecla física ESC no Windows. Se o usuário pressionar
3 vezes consecutivas em menos de 1200ms, o sistema aborta qualquer ação da IA,
revoga a autorização, solta teclas/mouse e emite alerta sonoro nativo.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import List, Callable, Optional
from .safety_gate import safety_gate
from .win32_types import VK_ESCAPE, ULONG_PTR

WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WH_KEYBOARD_LL = 13

class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Estrutura com informações de baixo nível de evento do teclado."""
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

if not hasattr(ctypes, "WINFUNCTYPE"):
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class EmergencyKillSwitch:
    """Gerencia a detecção de pânico global e cancelamento imediato no Windows."""

    def __init__(self, window_seconds: float = 1.2, required_presses: int = 3):
        self.window_seconds = window_seconds
        self.required_presses = required_presses
        self._press_timestamps: List[float] = []
        self._lock = threading.Lock()
        self._hook_id = None
        self._hook_thread: Optional[threading.Thread] = None
        self._running = False
        self._hook_proc_ref = None  # Previne garbage collection do delegate
        self._cleanup_callbacks: List[Callable[[], None]] = []

    def register_cleanup_callback(self, cb: Callable[[], None]) -> None:
        """Adiciona funções de liberação de emergência (mouse, teclado, etc.)."""
        with self._lock:
            if cb not in self._cleanup_callbacks:
                self._cleanup_callbacks.append(cb)

    def record_esc_press(self) -> bool:
        """Registra um pressionamento da tecla ESC. Retorna True se disparou o Kill-Switch."""
        agora = time.time()
        with self._lock:
            self._press_timestamps.append(agora)
            self._press_timestamps = [t for t in self._press_timestamps if agora - t <= self.window_seconds]
            if len(self._press_timestamps) >= self.required_presses:
                self._press_timestamps.clear()
                self._trigger_emergency_stop()
                return True
        return False

    def trigger_emergency_stop(self) -> None:
        """Dispara imediatamente a parada de emergência manual ou programática."""
        with self._lock:
            self._press_timestamps.clear()
        self._trigger_emergency_stop()

    def _trigger_emergency_stop(self) -> None:
        """Executa a rotina de pânico, revoga autorização e executa limpezas."""
        # 1. Revogação atômica imediata
        safety_gate.revoke("EMERGENCY_KILL_SWITCH_TRIGGERED (3x ESC)")
        
        # 2. Emissão de bipe sonoro nativo do Windows (MB_ICONHAND / 0x10)
        try:
            ctypes.windll.user32.MessageBeep(0x10)
        except Exception:
            pass

        # 3. Disparo das rotinas de liberação compulsória (soltura de teclas e mouse)
        for cb in list(self._cleanup_callbacks):
            try:
                cb()
            except Exception:
                pass

    def start(self) -> None:
        """Inicia o listener global em thread de segundo plano com Windows Hook."""
        if self._running:
            return
        self._running = True
        self._hook_thread = threading.Thread(target=self._hook_loop, daemon=True, name="KillSwitchHookThread")
        self._hook_thread.start()

    def stop(self) -> None:
        """Finaliza o hook global de forma limpa e descarrega o manipulador."""
        self._running = False
        if self._hook_id:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self._hook_id)
            except Exception:
                pass
            self._hook_id = None

    def _hook_loop(self) -> None:
        """Loop Win32 para recebimento de mensagens de teclado de baixo nível."""
        user32 = ctypes.windll.user32

        def low_level_keyboard_proc(n_code, w_param, l_param):
            if n_code >= 0 and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kbd = KBDLLHOOKSTRUCT.from_address(l_param)
                if kbd.vkCode == VK_ESCAPE:
                    self.record_esc_press()
            return user32.CallNextHookEx(self._hook_id, n_code, w_param, l_param)

        self._hook_proc_ref = HOOKPROC(low_level_keyboard_proc)
        self._hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._hook_proc_ref, ctypes.windll.kernel32.GetModuleHandleW(None), 0
        )

        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)  # PM_REMOVE = 1
            if b_ret > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)

# Instância padrão compartilhada do KillSwitch
kill_switch = EmergencyKillSwitch()
