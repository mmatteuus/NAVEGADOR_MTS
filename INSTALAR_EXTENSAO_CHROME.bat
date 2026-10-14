@echo off
setlocal EnableDelayedExpansion
title BROWSER MTS -- Instalador da Extensao do Navegador

echo ==============================================================================
echo       BROWSER MTS -- Instalador Simplificado da Extensao (Chrome / Edge)
echo ==============================================================================
echo.
echo Este assistente vai abrir o seu navegador e a pasta da extensao para voce.
echo Siga apenas estes 2 passos simples:
echo.
echo   [PASSO 1] Na aba do Chrome que vai abrir, ATIVE o "Modo do desenvolvedor"
echo             (fica no canto superior direito da tela).
echo.
echo   [PASSO 2] Clique no botao "Carregar sem compactacao" (canto superior esquerdo)
echo             e selecione a pasta da extensao que acabamos de abrir para voce!
echo             (Ou simplesmente arraste a pasta para dentro do navegador)
echo.
echo ==============================================================================
echo Pressione qualquer tecla para abrir o Chrome e a pasta agora...
pause >nul

:: Determinar o diretorio da extensao
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "EXTENSION_DIR=%PROJECT_DIR%\src\extension"

:: 1. Abrir a pasta da extensao no Windows Explorer
echo Abrindo a pasta da extensao no Windows Explorer...
explorer "%EXTENSION_DIR%"

:: 2. Tentar abrir o Google Chrome diretamente na tela de extensoes
echo Abrindo a pagina de extensoes no navegador...
start chrome "chrome://extensions/" 2>nul
if %ERRORLEVEL% neq 0 (
    :: Se o Chrome nao estiver no PATH, tenta pelo Edge
    start msedge "edge://extensions/" 2>nul
    if %ERRORLEVEL% neq 0 (
        start "" "chrome://extensions/"
    )
)

echo.
echo [PRONTO!] A pasta e o navegador foram abertos.
echo Basta clicar em "Carregar sem compactacao" e escolher a pasta aberta.
echo.
pause
