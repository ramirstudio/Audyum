; Installer per utente singolo, senza privilegi di amministratore.
; L'installer contiene solo il codice e uv.exe (pochi MB): Python, PyTorch CUDA e MMAudio
; vengono scaricati da setup_env.cmd durante l'installazione, i pesi dei modelli al primo utilizzo.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6B7C2F4E-3A1D-4E8B-9C55-A0D1E7F3B912}
AppName=Audyum
AppVersion={#AppVersion}
AppPublisher=Audyum
DefaultDirName={localappdata}\Programs\Audyum
DefaultGroupName=Audyum
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Audyum-Setup-{#AppVersion}
SetupIconFile=audyum.ico
UninstallDisplayIcon={app}\audyum.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ShowLanguageDialog=no

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\uv.lock"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\src\*"; DestDir: "{app}\src"; Excludes: "__pycache__,*.pyc"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "bin\uv.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "setup_env.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "audyum.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Audyum"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "-m audyum"; WorkingDir: "{app}"; IconFilename: "{app}\audyum.ico"
Name: "{autoprograms}\Audyum - ripara installazione"; Filename: "{app}\setup_env.cmd"; WorkingDir: "{app}"
Name: "{autodesktop}\Audyum"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "-m audyum"; WorkingDir: "{app}"; IconFilename: "{app}\audyum.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "-m audyum"; WorkingDir: "{app}"; Description: "Avvia Audyum"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\portable.txt"
Type: filesandordirs; Name: "{app}\src"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Scarico Python, PyTorch CUDA e MMAudio (circa 4 GB)...';
    if not Exec(ExpandConstant('{cmd}'), '/c ""' + ExpandConstant('{app}\setup_env.cmd') + '""',
                ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      MsgBox('La preparazione dell''ambiente non è riuscita. Controlla la connessione e usa ' +
             '"Audyum - ripara installazione" dal menu Start.', mbError, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Data: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Data := ExpandConstant('{app}\data');
    if DirExists(Data) then
      if MsgBox('Eliminare anche i modelli scaricati (circa 10 GB) in ' + Data + '?',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(Data, True, True, True);
  end;
end;
