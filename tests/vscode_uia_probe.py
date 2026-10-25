"""E2E opt-in de menus VS Code em perfil descartável e atribuído."""
from __future__ import annotations
import ctypes
import json
import os
import subprocess
import time
import psutil
from ctypes import wintypes
from pathlib import Path
from pywinauto import Desktop
from src.computer import execute_computer_action, safety_gate
from src.computer.window_assignments import window_assignments

ROOT = Path(__file__).resolve().parents[1] / "temp" / "vscode-public-uia-qa"
PROFILE = ROOT / "profile"
EXT = ROOT / "extensions"
WORKSPACE = ROOT / "Navegador-QA-Public-20261025.code-workspace"
CODE = Path(r"C:\Users\MATEUS\AppData\Local\Programs\Microsoft VS Code\Code.exe")
user32 = ctypes.windll.user32
SW_MINIMIZE = 6

def cursor_state():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return int(user32.GetForegroundWindow() or 0), (point.x, point.y)

def main() -> None:
    PROFILE.joinpath("User").mkdir(parents=True, exist_ok=True)
    EXT.mkdir(parents=True, exist_ok=True)
    WORKSPACE.write_text(json.dumps({"folders": [], "settings": {}}), encoding="utf-8")
    PROFILE.joinpath("User", "settings.json").write_text(json.dumps({"editor.accessibilitySupport": "on"}), encoding="utf-8")
    before_launch = cursor_state()
    args = [str(CODE), f"--user-data-dir={PROFILE}", f"--extensions-dir={EXT}", "--disable-extensions", "--new-window", "--skip-welcome", "--force-renderer-accessibility", str(WORKSPACE)]
    process = subprocess.Popen(args)
    try:
        title = "Navegador-QA-Public-20261025"
        window = None
        for _ in range(30):
            found = [item for item in Desktop(backend="uia").windows() if title in item.window_text()]
            if found:
                window = found[0]
                break
            time.sleep(0.5)
        assert window is not None, "VS Code descartável não abriu janela UIA"
        owned = {item.pid for item in psutil.process_iter(["pid", "cmdline"]) if any(f"--user-data-dir={PROFILE}" in arg for arg in (item.info.get("cmdline") or []))}
        assert window.element_info.process_id in owned and owned, (window.element_info.process_id, owned)
        user32.ShowWindow(wintypes.HWND(window.handle), SW_MINIMIZE)
        time.sleep(1)
        before_action = cursor_state()
        window_assignments.assign("vscode-public-qa", window.handle)
        safety_gate.authorize()
        result = execute_computer_action("computer_window_action", {"operation": "invoke", "selector": {"title": "Help"}, "session_id": "vscode-public-qa"})
        assert result["success"] and result["data"]["transport"] == "uia-expand", result
        after_action = cursor_state()
        assert after_action == before_action, (before_launch, before_action, after_action)
        time.sleep(0.5)
        owned_windows = [item for item in Desktop(backend="uia").windows() if item.element_info.process_id in owned]
        names = {item.element_info.name for root in owned_windows for item in root.descendants(control_type="MenuItem")}
        assert "Documentation" in names or "Open Walkthrough..." in names, sorted(names)
        window_assignments.release("vscode-public-qa")
        denied = execute_computer_action("computer_window_action", {"operation": "inspect", "session_id": "vscode-public-qa"})
        assert not denied["success"] and "TARGET_NOT_ASSIGNED" in denied["error"]
        print("PASS vscode_uia_probe: Help expand, menu postcondition, cursor/foreground stable, revoke denied")
    finally:
        safety_gate.revoke("probe cleanup")
        window_assignments.clear()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    main()
