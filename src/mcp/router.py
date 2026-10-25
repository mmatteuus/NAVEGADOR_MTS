"""Módulo Roteador de Ferramentas (MCP Tool Router).

Despacha requisições tools/call para a extensão via WebSocket Bridge ou para o motor
nativo de Computer Use sob a Trava de Segurança, garantindo validação de sessão e anti-forja.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from .session_manager import session_manager
from .session_context import get_current_session_id
from .response_formatter import format_mcp_result, format_mcp_error

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

    async def dispatch(
        self, tool_name: str, arguments: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Despacha a ferramenta solicitada para o executor correspondente com defesa anti-forja."""
        trusted_sid = session_id or get_current_session_id()
        arg_sids = [arguments[key] for key in ("sessionId", "session_id") if key in arguments]
        if len(arg_sids) > 1 and str(arg_sids[0]).strip() != str(arg_sids[1]).strip():
            return format_mcp_error("Acesso recusado: aliases de sessão divergentes.")
        if arg_sids:
            if not trusted_sid or str(arg_sids[0]).strip() != str(trusted_sid).strip():
                logger.warning("FORGERY BLOCKED: identidade de sessão nos argumentos não é confiável")
                return format_mcp_error("Acesso recusado: Tentativa de forja de sessão detectada (identidade não confiável).")
            trusted_sid = str(trusted_sid).strip()

        clean_args = {k: v for k, v in arguments.items() if k not in ("sessionId", "session_id")}
        if trusted_sid:
            clean_args["sessionId"] = trusted_sid

        try:
            if tool_name.startswith("browser_"):
                return await self._dispatch_browser(tool_name, clean_args, trusted_sid)
            elif tool_name.startswith("computer_"):
                return await self._dispatch_computer(tool_name, clean_args)
            return format_mcp_error(f"Ferramenta desconhecida: '{tool_name}'")
        except Exception as exc:
            logger.error(f"Erro ao executar {tool_name}: {exc}")
            return format_mcp_error(f"Falha na execução de {tool_name}: {exc}")

    async def _dispatch_browser(
        self, name: str, args: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Despacha ferramentas de navegador para a extensão via WebSocket Bridge."""
        if not self.ws_bridge or not self.ws_bridge.is_connected:
            return format_mcp_error("A extensão do navegador não está conectada.")

        tab_id = args.get("tabId")
        if tab_id is not None:
            try:
                if not session_manager.validate_tab_access(session_id, int(tab_id)):
                    return format_mcp_error(f"Acesso recusado: A aba {tab_id} pertence a outra sessão de agente.")
            except (ValueError, TypeError):
                pass

        res = await self.ws_bridge.send_action(name, args, session_id=session_id)

        if isinstance(res, dict) and res.get("success") is False:
            return format_mcp_error(str(res.get("error", "Falha na extensão")))

        # Criação não concede posse: somente a atribuição humana no popup pode
        # vincular a aba a uma sessão. Fechamento ainda limpa posse existente.
        if name == "browser_manage_tabs" and args.get("action") == "close":
            close_tid = args.get("tabId")
            if close_tid is not None:
                try:
                    session_manager.release_tab(int(close_tid))
                except (ValueError, TypeError):
                    pass

        if isinstance(res, dict) and res.get("success") is True and "data" in res:
            return format_mcp_result(res["data"])
        return format_mcp_result(res)

    async def _dispatch_computer(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Despacha ferramentas de computador respeitando a trava de segurança."""
        if name == "computer_get_status":
            return format_mcp_result({
                "authorized": self.is_computer_authorized(),
                "killSwitchActive": bool(self.kill_switch_checker())
            })

        if not self.is_computer_authorized():
            return format_mcp_error("Ação recusada: Controle do Computador não autorizado.")

        if not self.computer_executor:
            return format_mcp_error("Módulo de Computer Use não configurado ou indisponível.")

        res = await self.computer_executor(name, args)
        if isinstance(res, dict) and res.get("success") is False:
            return format_mcp_error(str(res.get("error", "Falha no computador")))
        if isinstance(res, dict) and res.get("success") is True and "data" in res:
            return format_mcp_result(res["data"])
        return format_mcp_result(res)

    def _format_result(self, result_data: Any) -> Dict[str, Any]:
        """Compatibilidade retroativa: delega para format_mcp_result."""
        return format_mcp_result(result_data)

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Compatibilidade retroativa: delega para format_mcp_error."""
        return format_mcp_error(message)
