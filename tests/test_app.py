import pytest
import asyncio
from unittest.mock import patch, MagicMock

from src.app import main

def test_main_keyboard_interrupt_desktop():
    """Testa se KeyboardInterrupt chama app.shutdown() no modo Desktop."""
    with patch("src.app.argparse.ArgumentParser.parse_args") as mock_args:
        args = MagicMock()
        args.stdio = False
        args.minimized = False
        mock_args.return_value = args

        with patch("src.app.DesktopApplication") as mock_desktop:
            app_instance = MagicMock()
            app_instance.run.side_effect = KeyboardInterrupt()
            mock_desktop.return_value = app_instance

            main()

            app_instance.shutdown.assert_called_once()


def test_main_keyboard_interrupt_stdio():
    """Testa se KeyboardInterrupt é tratado silenciosamente no modo stdio."""
    with patch("src.app.argparse.ArgumentParser.parse_args") as mock_args:
        args = MagicMock()
        args.stdio = True
        mock_args.return_value = args

        with patch("src.app.asyncio.run", side_effect=KeyboardInterrupt()) as mock_run:
            with patch("src.app.MCPServer"):
                main()

                # Verify that it caught KeyboardInterrupt (if it didn't, the test would crash)
                mock_run.assert_called_once()
                # Clean up unawaited coroutine
                coro = mock_run.call_args[0][0]
                coro.close()
