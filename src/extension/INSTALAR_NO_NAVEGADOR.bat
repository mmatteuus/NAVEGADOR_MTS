@echo off
chcp 65001 >nul
echo ========================================================
echo    INSTALADOR RAPIDO DA EXTENSAO BROWSER MTS
echo ========================================================
echo.
echo 1. O Google Chrome abrira na pagina de extensoes.
echo 2. Ative a chave 'Modo do desenvolvedor' (canto superior direito).
echo 3. Clique em 'Carregar sem compactacao'.
echo 4. Selecione esta pasta que acabou de abrir!
echo.
start chrome.exe chrome://extensions/ 2>nul || start msedge.exe edge://extensions/
start explorer.exe "%~dp0"
echo Pronto! A pasta da extensao foi aberta na sua tela.
timeout /t 5 >nul

