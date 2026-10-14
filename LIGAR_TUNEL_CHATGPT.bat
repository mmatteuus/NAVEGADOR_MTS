@echo off
chcp 65001 >nul
title BROWSER MTS - Túnel OpenAI (ChatGPT)
cls

echo =======================================================
echo   🌐 BROWSER MTS - Conectar ao ChatGPT (OpenAI Tunnel)
echo =======================================================
echo.

set "TUNNEL_EXE=C:\Users\MATEUS\browser mcp mts\BROWSER-MCP-MTS-PORTATIL\tunnel-client.exe"
set "CONFIG_YAML=C:\Users\MATEUS\browser mcp mts\BROWSER-MCP-MTS-PORTATIL\config\profiles\browser-mts-runtime.yaml"

if not exist "%TUNNEL_EXE%" (
    echo [ERRO] Binário tunnel-client.exe não encontrado em:
    echo "%TUNNEL_EXE%"
    echo.
    pause
    exit /b 1
)

echo [1/2] Verificando configuração do túnel...
echo Tunnel ID: tunnel_6a7aea545c408191889cd114d4a99d9b
echo Servidor MCP: BROWSER_MTS.exe --stdio
echo.
echo [2/2] Iniciando túnel seguro de conexão com a OpenAI...
echo.
echo =======================================================
echo   🟢 TÚNEL ATIVO!
echo   No ChatGPT, acesse "Adicionar servidor MCP personalizado":
echo   - Conexão: Selecione a aba "Túnel"
echo   - Cole: tunnel_6a7aea545c408191889cd114d4a99d9b
echo   - Autenticação: Sem autenticação
echo =======================================================
echo.
echo Mantenha esta janela aberta enquanto estiver usando no ChatGPT.
echo Para encerrar, feche esta janela.
echo.

"%TUNNEL_EXE%" run --config "%CONFIG_YAML%"

