"""Endpoint MCP Streamable HTTP local para conexão pelo túnel."""
from __future__ import annotations

from aiohttp import web
from .server import MCPServer


class MCPHTTPServer:
    """Transporte stateless no loopback; tráfego externo requer túnel autenticado."""

    def __init__(self, server: MCPServer, port: int, host: str = "127.0.0.1") -> None:
        if host != "127.0.0.1":
            raise ValueError("MCP HTTP deve usar 127.0.0.1.")
        self.server, self.port, self.host = server, port, host
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        if self._runner is not None:
            return
        app = web.Application(client_max_size=1024 * 1024,
                              middlewares=[self._validate_local_request])
        app.router.add_post("/mcp", self._post)
        app.router.add_get("/mcp", self._get)
        app.router.add_get("/healthz", self._health)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(runner, self.host, self.port).start()
        except Exception:
            await runner.cleanup()
            raise
        self._runner = runner

    async def stop(self) -> None:
        runner, self._runner = self._runner, None
        if runner is not None:
            await runner.cleanup()

    @web.middleware
    async def _validate_local_request(self, request: web.Request, handler):
        """Permite requisições vindas do loopback e do túnel (ChatGPT/OpenAI/Local).

        Protege contra DNS rebinding sem bloquear o encaminhamento de cabeçalhos pelo túnel.
        """
        # Garante que a conexão física é estritamente local (loopback)
        remote = request.remote
        if remote not in ("127.0.0.1", "::1", "localhost"):
            return web.Response(status=403, text="Acesso externo direto não permitido.")

        origin = request.headers.get("Origin")
        if origin:
            # Se a requisição contiver um cabeçalho Origin, aceita se for local ou das plataformas suportadas
            allowed_origin_prefixes = (
                f"http://127.0.0.1:{self.port}",
                f"http://localhost:{self.port}",
                "https://chatgpt.com",
                "https://chat.openai.com",
                "https://claude.ai",
            )
            if not any(origin.startswith(prefix) for prefix in allowed_origin_prefixes):
                return web.Response(status=403, text="Origin não autorizado.")

        return await handler(request)

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "browser-mcp-mts"})

    async def _get(self, request: web.Request) -> web.Response:
        return web.Response(status=405, headers={"Allow": "POST"})

    async def _post(self, request: web.Request) -> web.Response:
        if request.content_type != "application/json":
            return web.Response(status=415)
        try:
            message = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "JSON inválido"}}, status=400)
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return web.json_response({"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "Requisição inválida"}}, status=400)
        session_id = (
            request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID")
            or request.headers.get("mcp-session-id") or request.headers.get("x-session-id")
        )
        if session_id and isinstance(message.get("params"), dict):
            args = message["params"].setdefault("arguments", {})
            if isinstance(args, dict):
                args.setdefault("sessionId", session_id)
        result = await self.server.handle_jsonrpc(message)
        if result is None:
            return web.Response(status=202)
        negotiated = result.get("result", {}).get("protocolVersion") if isinstance(result, dict) else None
        version = negotiated or request.headers.get("MCP-Protocol-Version", "2025-06-18")
        headers = {"MCP-Protocol-Version": version}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return web.json_response(result, headers=headers)

