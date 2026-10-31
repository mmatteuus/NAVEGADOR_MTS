import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from src.app import main

class TestAppErrorHandling(unittest.TestCase):
    @patch('src.app.asyncio.run')
    def test_main_stdio_keyboard_interrupt(self, mock_asyncio_run):
        """Verifica se KeyboardInterrupt é tratado silenciosamente em modo stdio."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        with patch.object(sys, 'argv', ['app.py', '--stdio']):
            with patch('src.mcp.server.MCPServer') as MockMCPServer:
                # We need to mock start and run_stdio as AsyncMocks so they can be awaited,
                # although asyncio.run itself raises KeyboardInterrupt before evaluating.
                # However, since asyncio.run takes a coroutine, and raises immediately, the
                # coroutine object is never awaited and python warns about it.
                # Let's silence this warning by awaiting it or explicitly closing it if possible.
                main()
                MockMCPServer.assert_called_once()

        mock_asyncio_run.assert_called_once()
        # To avoid the 'coroutine was never awaited' warning, we can capture the coroutine passed to asyncio.run and close it
        coro = mock_asyncio_run.call_args[0][0]
        coro.close()

    @patch('src.app.DesktopApplication')
    def test_main_desktop_keyboard_interrupt(self, MockDesktopApplication):
        """Verifica se KeyboardInterrupt aciona app.shutdown() em modo desktop."""
        mock_app_instance = MagicMock()
        mock_app_instance.run.side_effect = KeyboardInterrupt()
        MockDesktopApplication.return_value = mock_app_instance

        with patch.object(sys, 'argv', ['app.py']):
            main()

        mock_app_instance.run.assert_called_once()
        mock_app_instance.shutdown.assert_called_once()

if __name__ == '__main__':
    unittest.main()
