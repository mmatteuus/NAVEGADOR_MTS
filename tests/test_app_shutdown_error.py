import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.app import DesktopApplication

def test_desktop_application_shutdown_handles_exception():
    """Testa se a exceção no asyncio.run_coroutine_threadsafe é capturada corretamente e ignorada,
    permitindo o encerramento seguro (graceful shutdown)."""
    app = DesktopApplication()

    # Configurando o mock para o ws_loop
    app.ws_loop = MagicMock()
    app.ws_loop.is_running.return_value = True

    # Configurando o mock para o window
    app.window = MagicMock()

    # Mockando o Future retornado por asyncio.run_coroutine_threadsafe
    # para lançar uma exceção simulando TimeoutError ou outro erro durante o desligamento dos servidores
    mock_future = MagicMock()
    mock_future.result.side_effect = Exception("Test exception during shutdown")

    with patch("src.app.asyncio.run_coroutine_threadsafe", return_value=mock_future) as mock_run:
        with patch("src.app.kill_switch"):
            with patch("src.app.tunnel_service"):
                # Chama a função que deve tratar a exceção adequadamente
                app.shutdown()

                # Consome o coroutine criado pela função aninhada para evitar aviso de Memory Leak/RuntimeWarning "coroutine never awaited" no pytest
                args, kwargs = mock_run.call_args
                coroutine = args[0]
                coroutine.close()

                # Verifica que run_coroutine_threadsafe foi realmente chamada
                mock_run.assert_called_once()

                # Mesmo com a exceção, o código deve continuar e parar o loop do websockets (call_soon_threadsafe(ws_loop.stop()))
                app.ws_loop.call_soon_threadsafe.assert_called_once_with(app.ws_loop.stop())

                # Por fim, mesmo com a exceção, o código deve continuar e destruir a janela, que é o último passo
                app.window.destroy.assert_called_once()
