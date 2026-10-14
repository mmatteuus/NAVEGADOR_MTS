@echo off
chcp 65001 >nul
title BROWSER MTS - Atualizar Aplicação Instalada
cls

echo ==============================================================================
echo        🔄 BROWSER MTS -- Atualizar Aplicação Instalada para a Versão 2.0
echo ==============================================================================
echo.
echo Este utilitário atualiza sua aplicação já instalada com todas as novidades:
echo   ✨ Transporte Stdio MCP integrado
echo   ✨ Conector direto do ChatGPT (OpenAI Tunnel)
echo   ✨ Execução de aplicativos locais pelo agente (Excel, Bloco de Notas, etc.)
echo   ✨ Botão 1-clique para Conectar com IA no app
echo.
echo ==============================================================================
echo.

set "INSTALLER=%~dp0dist_installer\BROWSER_MTS_Instalador_v2.0.exe"

if not exist "%INSTALLER%" (
    echo [INFO] Instalador executável não encontrado. Compilando agora mesmo...
    py -3.14 "%~dp0build_installer.py"
)

echo [1/3] Encerrando processos anteriores para liberar substituição de arquivos...
taskkill /f /im BROWSER_MTS.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/3] Executando o instalador da versão atualizada...
echo Aguarde a conclusão do instalador...
start /wait "" "%INSTALLER%" /SILENT

echo [3/3] Iniciando o BROWSER MTS atualizado...
set "APP_EXE=%LOCALAPPDATA%\Programs\BROWSER MTS\BROWSER_MTS.exe"
if exist "%APP_EXE%" (
    start "" "%APP_EXE%"
    echo.
    echo ==============================================================================
    echo   ✅ APLICAÇÃO ATUALIZADA E INICIADA COM SUCESSO!
    echo ==============================================================================
) else (
    echo.
    echo [SUCESSO] Atualização concluída. Você pode abrir o BROWSER MTS pelo Menu Iniciar.
)

echo.
pause
