"""
Módulo Roteador de Ferramentas (MCP Tool Router).

Despacha requisições de ferramentas (tools/call) para a extensão do navegador
via WebSocket Bridge ou para o motor nativo de Computer Use sob a Trava de Segurança.
Padroniza as respostas de acordo com a especificação Model Context Protocol.
"""
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("BrowserMTS.Router")


class MCPToolRouter:
    """Roteador dinâmico de ferramentas MCP do BROWSER MTS."""

    def __init__(
        self,
        ws_bridge: Optional[Any] = None,
        computer_executor: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
        safety_checker: Optional[Callable[[], bool]] = None,
        kill_switch_checker: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.ws_bridge = ws_bridge
        self.computer_executor = computer_executor
        self.safety_checker = safety_checker or (lambda: False)
        self.kill_switch_checker = kill_switch_checker or (lambda: False)

    def is_computer_authorized(self) -> bool:
        """Consulta se o controle de computador está explicitamente autorizado."""
        try:
            return bool(self.safety_checker())
        except Exception:
            return False

    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Despacha a ferramenta solicitada para o executor correspondente."""
        try:
            if tool_name.startswith("browser_"):
                return await self._dispatch_browser(tool_name, arguments)
            elif tool_name.startswith("computer_"):
                return await self._dispatch_computer(tool_name, arguments)
            else:
                return self._error_response(f"Ferramenta desconhecida: '{tool_name}'")
        except Exception as exc:
            logger.error(f"Erro ao executar {tool_name}: {exc}")
            return self._error_response(f"Falha na execução de {tool_name}: {exc}")

    async def _dispatch_browser(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Despacha ferramentas de navegador para a extensão via WebSocket Bridge."""
        if not self.ws_bridge or not self.ws_bridge.is_connected:
            msg = (
                "A extensão do navegador não está conectada. "
                "Verifique se o navegador está aberto e se a extensão Browser MTS está ligada."
            )
            return self._error_response(msg)

        res = await self.ws_bridge.send_action(name, args)
        if isinstance(res, dict) and res.get("success") is False:
            return self._error_response(str(res.get("error", "Falha na extensão")))
        if isinstance(res, dict) and res.get("success") is True and "data" in res:
            return self._format_result(res["data"])
        return self._format_result(res)

    async def _dispatch_computer(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Despacha ferramentas de computador respeitando a trava de segurança."""
        if name == "computer_get_status":
            status = {"authorized": self.is_computer_authorized(),
                      "killSwitchActive": bool(self.kill_switch_checker())}
            return self._format_result(status)

        if not self.is_computer_authorized():
            msg = "Ação recusada: Controle do Computador não autorizado pelo usuário no aplicativo desktop."
            return self._error_response(msg)

        if not self.computer_executor:
            return self._error_response("Módulo de Computer Use não configurado ou indisponível.")

        res = await self.computer_executor(name, args)
        if isinstance(res, dict) and res.get("success") is False:
            return self._error_response(str(res.get("error", "Falha no computador")))
        if isinstance(res, dict) and res.get("success") is True and "data" in res:
            return self._format_result(res["data"])
        return self._format_result(res)

    def _format_result(self, result_data: Any) -> Dict[str, Any]:
        """Converte resultados arbitrários em conteúdo estruturado compatível com o MCP."""
        content = []
        if isinstance(result_data, dict) and any(
            k in result_data for k in ("base64", "screenshot", "imageBase64")
        ):
            b64_img = result_data.get("base64") or result_data.get("screenshot") or result_data.get("imageBase64")
            mime = result_data.get("mimeType") or ("image/jpeg" if result_data.get("format") in ("jpeg", "jpg") else "image/png")
            content.append({"type": "image", "data": str(b64_img), "mimeType": mime})
            info = {k: v for k, v in result_data.items() if k not in ("base64", "screenshot", "imageBase64")}
            if info:
                content.append({"type": "text", "text": json.dumps(info, ensure_ascii=False, indent=2)})
        else:
            text_repr = result_data if isinstance(result_data, str) else json.dumps(result_data, ensure_ascii=False, indent=2)
            content.append({"type": "text", "text": text_repr})

        return {"content": content, "isError": False}

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Gera envelope de erro padronizado para o protocolo MCP."""
        return {"content": [{"type": "text", "text": message}], "isError": True}
