"""Endpoint MCP Streamable HTTP local para conexão pelo túnel."""
import uuid
from aiohttp import web
from .server import MCPServer


def _extract_session_header(request: web.Request) -> str | None:
    """Extrai o identificador de sessão dos cabeçalhos HTTP suportados."""
    sid = (
        request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID")
        or request.headers.get("mcp-session-id") or request.headers.get("x-session-id")
    )
    return str(sid).strip() if sid and str(sid).strip() else None


class MCPHTTPServer:
    """Transporte com identidade por sessão; tráfego externo requer túnel autenticado."""

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
        app.router.add_delete("/mcp", self._delete)
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
        """Permite requisições vindas do loopback e do túnel (ChatGPT/Claude/Gemini/Local)."""
        remote = request.remote
        if remote not in ("127.0.0.1", "::1", "localhost"):
            return web.Response(status=403, text="Acesso externo direto não permitido.")

        origin = request.headers.get("Origin")
        if origin:
            allowed_origins = {
                f"http://127.0.0.1:{self.port}",
                f"http://localhost:{self.port}",
                "https://chatgpt.com",
                "https://chat.openai.com",
                "https://claude.ai",
                "https://gemini.google.com",
                "https://aistudio.google.com",
            }
            if origin not in allowed_origins:
                return web.Response(status=403, text="Origin não autorizado.")

        return await handler(request)

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "browser-mcp-mts"})

    async def _get(self, request: web.Request) -> web.Response:
        return web.Response(status=405, headers={"Allow": "POST, DELETE"})

    async def _delete(self, request: web.Request) -> web.Response:
        """Encerra explicitamente uma sessão MCP Streamable HTTP e libera recursos."""
        session_id = _extract_session_header(request)
        if not session_id:
            return web.json_response({"error": "SESSION_REQUIRED"}, status=400)
        from .session_manager import session_manager
        from .agent_directory import announce_agents
        closed = await session_manager.close_session(session_id)
        if not closed:
            return web.json_response({"error": "SESSION_NOT_FOUND", "sessionId": session_id}, status=404)
        await announce_agents(self.server.ws_bridge)
        return web.json_response({"status": "closed", "sessionId": session_id}, status=200)

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

        session_id = _extract_session_header(request)
        if message.get("method") == "tools/call":
            from .session_manager import session_manager
            session = session_manager.get_session(session_id) if session_id else None
            if not session or session.status != "active":
                code = "SESSION_NOT_FOUND" if session_id else "SESSION_REQUIRED"
                return web.json_response({"jsonrpc": "2.0", "id": message.get("id"),
                    "error": {"code": -32000, "message": f"{code}: inicialize uma sessão MCP antes de usar ferramentas."}},
                    status=404 if session_id else 400)

        if message.get("method") == "initialize" and not session_id:
            session_id = f"sess_{uuid.uuid4().hex}"

        from .session_context import set_current_session_id, reset_current_session_id
        token = set_current_session_id(session_id)
        try:
            result = await self.server.handle_jsonrpc(message, session_id=session_id)
        finally:
            reset_current_session_id(token)

        if message.get("method") == "initialize" and session_id:
            from .session_manager import session_manager
            sess = session_manager.get_session(session_id)
            if sess is not None:
                sess.transport = "http"

        headers = {"Access-Control-Expose-Headers": "Mcp-Session-Id, MCP-Protocol-Version"}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if result is None:
            return web.Response(status=202, headers=headers)
        negotiated = result.get("result", {}).get("protocolVersion") if isinstance(result, dict) else None
        headers["MCP-Protocol-Version"] = negotiated or request.headers.get("MCP-Protocol-Version", "2025-06-18")
        return web.json_response(result, headers=headers)
