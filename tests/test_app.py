import time
from unittest.mock import MagicMock, patch

from src.app import DesktopApplication


def test_desktop_application_http_mcp_oserror():
    app = DesktopApplication()

    async def mock_start():
        raise OSError("Address already in use")

    async def mock_ws_start():
        pass

    app.http_mcp.start = MagicMock(side_effect=mock_start)
    app.ws_bridge.start = MagicMock(side_effect=mock_ws_start)

    with patch("src.app.kill_switch.start"), patch("src.app.tunnel_service.start"):
        app._start_background_services()

        # allow thread to run
        time.sleep(0.5)

        assert app.http_error == "Address already in use"

        app.shutdown()
