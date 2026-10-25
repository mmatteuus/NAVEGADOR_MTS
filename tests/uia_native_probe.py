"""Probe opt-in UIA com uma janela EDIT nativa própria e oculta."""
from __future__ import annotations
import ctypes
import asyncio
import threading
import sys
import time
from ctypes import wintypes
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "temp" / "qa-python"))
from src.computer import execute_computer_action, safety_gate
from src.mcp.computer_dispatch import execute_mcp_computer
from src.computer.window_assignments import window_assignments

user32 = ctypes.windll.user32
WS_POPUP, WS_VISIBLE, ES_MULTILINE = 0x80000000, 0x10000000, 0x0004
BS_AUTOCHECKBOX = 0x0003

def pump(seconds=0.3):
    msg = wintypes.MSG()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.01)

def main():
    ready = threading.Event(); stop = threading.Event(); handles = {}
    def gui_fixture():
        handles["edit"] = int(user32.CreateWindowExW(0, "EDIT", "", WS_POPUP | WS_VISIBLE | ES_MULTILINE, 100, 100, 300, 80, 0, 0, 0, None))
        handles["button"] = int(user32.CreateWindowExW(0, "BUTTON", "QA", WS_POPUP | WS_VISIBLE | BS_AUTOCHECKBOX, 100, 200, 160, 40, 0, 0, 0, None))
        ready.set()
        while not stop.is_set(): pump(0.1)
        user32.DestroyWindow(handles["edit"]); user32.DestroyWindow(handles["button"])
    pump_thread = threading.Thread(target=gui_fixture, daemon=True); pump_thread.start(); ready.wait(5)
    hwnd, button = handles["edit"], handles["button"]
    if not hwnd or not button: raise RuntimeError("fixture creation failed")
    def call(name, args):
        return asyncio.run(asyncio.wait_for(execute_mcp_computer(name, args), timeout=5))
    try:
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        before = (int(user32.GetForegroundWindow() or 0), (point.x, point.y))
        window_assignments.assign("uia-probe", int(hwnd))
        safety_gate.authorize()
        found = call("computer_window_action", {"operation": "inspect", "sessionId": "uia-probe"})
        print("inspect", found.get("success"), len(found.get("data", {}).get("elements", [])))
        assert found.get("success") and found["data"]["elements"]
        selector = {"ref": found["data"]["elements"][0]["ref"]}
        result = call("computer_window_action", {"operation": "set_value", "selector": selector, "value": "uia-agent", "sessionId": "uia-probe"})
        print("set_value", result)
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        assert result["success"] and buf.value == "uia-agent"
        shot = call("computer_screenshot", {"sessionId": "uia-probe", "background": True})
        assert shot["success"] and shot["data"]["targetHwnd"] == int(hwnd)
        user32.GetCursorPos(ctypes.byref(point))
        after = (int(user32.GetForegroundWindow() or 0), (point.x, point.y))
        print("focus", before, after)
        assert after == before
        window_assignments.release("uia-probe")
        denied = call("computer_window_action", {"operation": "inspect", "sessionId": "uia-probe"})
        print("revoked", denied)
        assert not denied["success"] and "TARGET_NOT_ASSIGNED" in denied["error"]
        window_assignments.assign("uia-button", int(button))
        button_refs = call("computer_window_action", {"operation": "inspect", "sessionId": "uia-button"})
        assert button_refs["success"] and button_refs["data"]["elements"]
        button_ref = {"ref": button_refs["data"]["elements"][0]["ref"]}
        invoked = call("computer_window_action", {"operation": "invoke", "selector": button_ref, "sessionId": "uia-button"})
        print("button", invoked)
        assert invoked["success"]
        assert user32.SendMessageW(button, 0x00F0, 0, 0) == 1
        user32.GetCursorPos(ctypes.byref(point))
        assert (int(user32.GetForegroundWindow() or 0), (point.x, point.y)) == before
    finally:
        safety_gate.revoke("probe cleanup")
        window_assignments.clear(); stop.set(); pump_thread.join(timeout=3)

if __name__ == "__main__": main()
