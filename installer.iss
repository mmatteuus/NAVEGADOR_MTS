; Script de Criacao do Instalador Oficial Windows do BROWSER MTS
; Compilado com Inno Setup 6

#define MyAppName "BROWSER MTS"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "MTS Automacao & IA"
#define MyAppExeName "BROWSER_MTS.exe"

[Setup]
AppId={{C6B5E8A1-94F2-4D6F-B9D1-7A3982F10E23}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist_installer
OutputBaseFilename=BROWSER_MTS_Instalador_v2.0
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
DisableProgramGroupPage=auto

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "exticon"; Description: "Criar atalho na Area de Trabalho para a Extensao Chrome"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\BROWSER_MTS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\Pasta da Extensao Chrome"; Filename: "{app}\extension"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Extensao Chrome BROWSER MTS"; Filename: "{app}\extension"; Tasks: exticon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\extension\INSTALAR_NO_NAVEGADOR.bat"; Description: "Abrir navegador e pasta da extensao para ativacao rapida"; Flags: nowait postinstall skipifsilent shellexec

