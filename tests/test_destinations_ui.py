"""Regressão de construção real dos destinos sem servidor nem entrada física."""
from __future__ import annotations

from src.ui.main_window import MainWindow


def test_destinations_construct_and_fit_minimum_window(monkeypatch):
    """Detecta conflito com métodos internos Tk e botões inacessíveis por corte."""
    def setup(window):
        window.title("NAVEGADOR MTS - QA descartavel")
        window.geometry("760x580+30000+30000")
        window.minsize(760, 580)

    monkeypatch.setattr(MainWindow, "_setup_window", setup)
    monkeypatch.setattr("src.ui.window_assignment_panel.list_windows", lambda: [])
    window = MainWindow()
    try:
        window.update()
        window.update_idletasks()
        buttons = [window.btn_nav_dash, window.btn_nav_settings, window.btn_nav_windows,
                   window.btn_mcp_connect, window.btn_theme_toggle, window.btn_update]
        bounds = sorted((b.winfo_x(), b.winfo_x() + b.winfo_width()) for b in buttons)
        assert all(right <= buttons[0].master.winfo_width() for _left, right in bounds)
        assert all(a[1] <= b[0] for a, b in zip(bounds, bounds[1:]))
        window.show_windows()
        window.update_idletasks()
        assert window.panel_windows.winfo_manager() == "grid"
        assert not window.panel_dashboard.winfo_manager()
        assert window.panel_windows.windows.sessions.cget("state") == "readonly"
        assert window.panel_windows.folders.session.cget("state") == "readonly"
        window.show_settings()
        window.update_idletasks()
        assert not window.panel_windows.winfo_manager()
    finally:
        window.destroy()
