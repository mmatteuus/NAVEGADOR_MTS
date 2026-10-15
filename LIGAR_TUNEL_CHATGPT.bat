@echo off
setlocal
cd /d "%~dp0"
title Navegador MTS - Diagnostico do ChatGPT Tunnel
echo.
echo Verificando servidor MCP local e iniciando o aplicativo quando necessario...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TESTAR_INTEGRACAO.ps1" -StartApp
if errorlevel 1 (
  echo [ERRO] Verifique a instalacao, a porta 3457 e os logs locais.
  pause
  exit /b 1
)
echo.
echo O aplicativo tenta iniciar o tunnel-client se chave e Tunnel ID estiverem configurados.
echo Processo local nao comprova conexao com a OpenAI.
echo Confira a prontidao do cliente e vincule o Tunnel ID no ChatGPT.
pause
