; Assistente de instalação do AMS Translator (Inno Setup 6).
; Compilar: installer\build_installer.ps1  (ou abrir este .iss no Inno Setup Compiler)
; Requer a pasta ..\dist\AMS Translator\  (gere com build_exe.bat).

#define AppName "AMS Translator"
#define AppVersion "1.2.0"
#define AppPublisher "Alehandro Mendes"
#define AppExe "AMS Translator.exe"
#define AppUrl "https://github.com/alehandromendes/ams-translator"
#define DistDir "..\dist\AMS Translator"

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
OutputBaseFilename=AMSTranslatorSetup
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
; dados do usuário (config, traduções baixadas, backups) ficam em
; %LOCALAPPDATA%\AMS Translator por padrão — só saem se o usuário confirmar
; no prompt abaixo ([Code] CurUninstallStepChanged).
Type: filesandordirs; Name: "{app}\_internal"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
  Msg: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\AMS Translator');
    if DirExists(DataDir) then
    begin
      Msg := 'Apagar também as traduções baixadas, configurações e backups?' + #13#10 + #13#10 +
        DataDir + #13#10 + #13#10 +
        'Escolha Não se for reinstalar depois — assim não precisa baixar as ' +
        'traduções de novo.';
      if MsgBox(Msg, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
