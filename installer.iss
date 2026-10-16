; Script de Criacao do Instalador Oficial Windows do Navegador MTS
; Compilado com Inno Setup 6

#define MyAppName "NAVEGADOR MTS"
#ifndef MyAppVersion
  #define MyAppVersion "2.2.0"
#endif
#define MyAppPublisher "MTS Automacao & IA"
#define MyAppExeName "NAVEGADOR_MTS.exe"

[Setup]
AppId={{3D097DD4-9344-4816-A07E-E1E169EDFFFC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist_installer
OutputBaseFilename=NAVEGADOR_MTS_Instalador_v{#MyAppVersion}
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
DisableWelcomePage=yes
DisableDirPage=auto
DisableProgramGroupPage=auto
DisableReadyPage=yes
DisableFinishedPage=yes
CloseApplications=force
CloseApplicationsFilter=NAVEGADOR_MTS.exe,NAVEGADOR_MTS_MCP.exe,tunnel-client.exe,cloudflared.exe
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "exticon"; Description: "Criar atalho na Area de Trabalho para a Extensao Chrome"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "installer\close_owned_processes.ps1"; DestDir: "{tmp}"; Flags: dontcopy
Source: "dist\NAVEGADOR_MTS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace
Source: "src\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\Pasta da Extensao Chrome"; Filename: "{app}\extension"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Extensao Chrome NAVEGADOR MTS"; Filename: "{app}\extension"; Tasks: exticon; IconFilename: "{app}\app_icon.ico"
; Não criar atalhos na raiz de D:.
; A extensão permanece acessível pelo grupo de programas e área de trabalho.

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait

[Code]
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\{#MyAppExeName}'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  ExtractTemporaryFile('close_owned_processes.ps1');
  if not Exec(ExpandConstant('{sysnative}\WindowsPowerShell\v1.0\powershell.exe'),
    ExpandConstant('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{tmp}\close_owned_processes.ps1" -InstallDir "{app}"'),
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    Result := 'Não foi possível fechar os processos do NAVEGADOR MTS na pasta instalada.'
  else
    Result := '';
end;
