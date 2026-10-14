@echo off
setlocal
set "BROWSER_MTS_ROOT=%~dp0"
echo.
echo BROWSER MTS - Configurar Runtime API Key
echo Copie a NOVA chave para a area de transferencia antes de continuar.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=$env:BROWSER_MTS_ROOT; $config=Join-Path $root 'config'; New-Item -ItemType Directory -Force -Path $config | Out-Null; $key=(Get-Clipboard -Raw).Trim(); if([string]::IsNullOrWhiteSpace($key) -or -not $key.StartsWith('sk-')){ throw 'A area de transferencia nao contem uma chave OpenAI valida.' }; $keyFile=Join-Path $config 'runtime-api-key.txt'; [IO.File]::WriteAllText($keyFile,$key,[Text.UTF8Encoding]::new($false)); & icacls.exe $keyFile /inheritance:r /grant:r "${env:USERNAME}:F" | Out-Null; Write-Host ('Chave salva em: ' + $keyFile) -ForegroundColor Green"
if errorlevel 1 (
  echo.
  echo Falha ao configurar a chave.
  pause
  exit /b 1
)
echo.
echo Configuracao concluida. Agora voce pode abrir BROWSER MTS.exe.
pause
