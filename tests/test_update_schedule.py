"""Contrato comportamental da verificação periódica sem instalação automática."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.update_models import UpdateInfo
from src.ui.main_window import MainWindow


class FakeWindow:
    """Scheduler mínimo para exercitar a lógica real sem abrir uma janela."""

    def __init__(self):
        self.latest_update_info = None
        self.on_quit_app = None
        self._update_timer = None
        self._update_dialog = None
        self._update_check_in_flight = False
        self.check_for_updates_ui = MagicMock()
        self.btn_update = MagicMock()
        self.cancelled = []
        self.scheduled = []

    def after_cancel(self, token):
        self.cancelled.append(token)

    def after(self, delay, callback):
        token = f"timer-{len(self.scheduled)}"
        self.scheduled.append((token, delay, callback))
        if delay == 0:
            callback()
        return token


def test_hourly_rearm_guard_and_single_popup_without_consent():
    """A checagem rearma, cancela o timer anterior e não baixa sem clique."""
    fake = FakeWindow()
    info = UpdateInfo("2.1.4", "Notas", "https://mock/setup.exe", "setup.exe", True)
    dialog = MagicMock()
    dialog.winfo_exists.return_value = True
    check = MagicMock(return_value=info)
    def thread_factory(target, **_kwargs):
        return SimpleNamespace(start=target)
    with patch("src.core.updater.check_for_updates", check), \
         patch("src.ui.update_dialog.UpdateDialog", return_value=dialog) as popup, \
         patch("threading.Thread", side_effect=thread_factory):
        MainWindow.check_for_updates_ui(fake, auto_open=True)
        assert fake._update_timer is not None
        fake.scheduled[1][2]()
        fake.check_for_updates_ui.assert_called_once_with(auto_open=True)
        fake._update_check_in_flight = True
        MainWindow.check_for_updates_ui(fake, auto_open=True)
        assert check.call_count == 1
        fake._update_check_in_flight = False
        MainWindow.check_for_updates_ui(fake, auto_open=True)

    assert fake.cancelled == ["timer-1"]
    assert popup.call_count == 1
    assert dialog.btn_apply.invoke.call_count == 0
