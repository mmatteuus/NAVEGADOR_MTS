"""Ensaio opt-in de dois HWNDs nativos atribuídos a sessões simultâneas."""
from __future__ import annotations
import asyncio, ctypes, sys, threading, time
from ctypes import wintypes
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.computer import execute_computer_action, safety_gate
from src.computer.window_assignments import window_assignments
from src.mcp.computer_dispatch import execute_mcp_computer

u32 = ctypes.windll.user32
POPUP, VISIBLE, MULTI, AUTO = 0x80000000, 0x10000000, 4, 3
WM_GETTEXT, WM_GETTEXTLENGTH, BM_GETCHECK = 0xD, 0xE, 0xF0

def text(hwnd: int) -> str:
    size = u32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(size + 1)
    u32.GetWindowTextW(hwnd, buf, size + 1)
    return buf.value

def main() -> None:
    ready, stop, handles = threading.Event(), threading.Event(), {}
    def gui() -> None:
        for sid, x in (("a", 40), ("b", 420)):
            handles[f"edit-{sid}"] = int(u32.CreateWindowExW(
                0, "EDIT", "", POPUP | VISIBLE | MULTI, x, 100, 260, 60, 0, 0, 0, None))
            handles[f"button-{sid}"] = int(u32.CreateWindowExW(
                0, "BUTTON", "QA", POPUP | VISIBLE | AUTO, x, 180, 120, 40, 0, 0, 0, None))
        ready.set()
        msg = wintypes.MSG()
        while not stop.is_set():
            while u32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                u32.TranslateMessage(ctypes.byref(msg)); u32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(.005)
        for hwnd in handles.values(): u32.DestroyWindow(hwnd)
    thread = threading.Thread(target=gui, daemon=True); thread.start()
    if not ready.wait(5): raise RuntimeError("fixture não iniciou")
    edits = [handles["edit-a"], handles["edit-b"]]
    buttons = [handles["button-a"], handles["button-b"]]
    async def call(name: str, args: dict) -> dict:
        return await execute_mcp_computer(name, args)
    async def scenario() -> None:
        await asyncio.gather(*(
            call("computer_keyboard_action", {"action": "type", "text": value, "sessionId": sid})
            for sid, value in (("native-a", "alpha"), ("native-b", "bravo"))))
        assert text(edits[0]) == "alpha" and text(edits[1]) == "bravo"
        denied = await call("computer_keyboard_action", {
            "action": "type", "text": "x", "sessionId": "native-a", "hwnd": edits[1]})
        assert not denied["success"] and "TARGET_NOT_ASSIGNED" in denied["error"]
        await asyncio.gather(*(
            call("computer_mouse_action", {"action": "click", "x": 5, "y": 5,
                 "hwnd": hwnd, "sessionId": sid})
            for sid, hwnd in (("native-a", buttons[0]), ("native-b", buttons[1]))))
        assert u32.SendMessageW(buttons[0], BM_GETCHECK, 0, 0) == 1
        assert u32.SendMessageW(buttons[1], BM_GETCHECK, 0, 0) == 1
    try:
        safety_gate.authorize()
        for sid, hwnd in zip(("native-a", "native-b"), edits): window_assignments.assign(sid, hwnd)
        point = wintypes.POINT(); u32.GetCursorPos(ctypes.byref(point))
        before = (int(u32.GetForegroundWindow() or 0), point.x, point.y)
        asyncio.run(scenario())
        u32.GetCursorPos(ctypes.byref(point))
        assert before == (int(u32.GetForegroundWindow() or 0), point.x, point.y)
        print("NATIVE_TWO_AGENTS_PASS", edits, buttons, before)
    finally:
        safety_gate.revoke("probe cleanup"); window_assignments.clear(); stop.set(); thread.join(3)

if __name__ == "__main__": main()
