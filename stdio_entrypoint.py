"""Entrada de console do MCP para clientes stdio (PyInstaller --console)."""
from __future__ import annotations

import asyncio
from src.core.config import current_config
from src.mcp.server import MCPServer


async def main() -> None:
    server = MCPServer(host=current_config.host, ws_port=current_config.port)
    try:
        await server.start()
        await server.run_stdio()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
