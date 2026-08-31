; Assistente de instalação do Tradutor de Legendas (Inno Setup 6).
; Compilar: installer\build_installer.ps1  (ou abrir este .iss no Inno Setup Compiler)
; Requer a pasta ..\dist\Tradutor de Legendas\  (gere com build_exe.bat).

#define AppName "Tradutor de Legendas"
#define AppVersion "1.1.0"
#define AppPublisher "Alehandro Mendes"
#define AppExe "Tradutor de Legendas.exe"
#define AppUrl "https://github.com/alehandromendes/tradutor-legendas"
#define DistDir "..\dist\Tradutor de Legendas"

[Setup]
AppId={{B6F3B6A2-7B2E-4E1C-9E0C-7A1D2C3D4E5F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=TradutorDeLegendasSetup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#DistDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallDelete]
; dados do usuário ficam em %LOCALAPPDATA%\TradutorDeLegendas e NÃO são removidos.
Type: filesandordirs; Name: "{app}\_internal"
