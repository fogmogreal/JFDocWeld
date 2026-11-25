[Setup]
AppId={{8F4B2C1A-9E3D-4A7B-B5C2-1D8E9F0A3B4C}
AppName=JF DocWeld
AppVersion=1.0.0
AppPublisher=JF Weld
DefaultDirName={autopf}\JFDocWeld
DefaultGroupName=JF DocWeld
PrivilegesRequired=lowest
OutputDir=instalador_final
OutputBaseFilename=Instalador_JF_DocWeld
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=jfdocweld.ico
UninstallDisplayIcon={app}\JFDocWeld.exe

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\JFDocWeld\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\JF DocWeld"; Filename: "{app}\JFDocWeld.exe"
Name: "{group}\Desinstalar JF DocWeld"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JF DocWeld"; Filename: "{app}\JFDocWeld.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\JFDocWeld.exe"; Description: "{cm:LaunchProgram,JF DocWeld}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\JFDocWeld"