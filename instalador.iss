#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8F4B2C1A-9E3D-4A7B-B5C2-1D8E9F0A3B4C}
AppName=JF DocWeld
AppVersion={#AppVersion}
AppPublisher=JF Weld
DefaultDirName={autopf}\JFDocWeld
DefaultGroupName=JF DocWeld
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Setup_JFDocWeld
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
Source: "dist\JFDocWeld.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "jfdocweld.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\JF DocWeld"; Filename: "{app}\JFDocWeld.exe"; IconFilename: "{app}\jfdocweld.ico"
Name: "{group}\Desinstalar JF DocWeld"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JF DocWeld"; Filename: "{app}\JFDocWeld.exe"; IconFilename: "{app}\jfdocweld.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\JFDocWeld.exe"; Description: "{cm:LaunchProgram,JF DocWeld}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\JFDocWeld"
