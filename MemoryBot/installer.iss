[Setup]
AppName=Memory Bot
AppVersion=1.0
DefaultDirName={localappdata}\Programs\MemoryBot
DefaultGroupName=Memory Bot
PrivilegesRequired=lowest
OutputDir=installer_out
OutputBaseFilename=MemoryBot-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MemoryBot.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Snelkoppeling op het bureaublad"

[Files]
Source: "dist\MemoryBot\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Memory Bot"; Filename: "{app}\MemoryBot.exe"
Name: "{autodesktop}\Memory Bot"; Filename: "{app}\MemoryBot.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MemoryBot.exe"; Parameters: "--setup"; StatusMsg: "Chrome downloaden (eenmalig, even geduld)..."; Flags: runhidden waituntilterminated
Filename: "{app}\MemoryBot.exe"; Description: "Memory Bot starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\MemoryBot\chrome-win64"
Type: filesandordirs; Name: "{localappdata}\MemoryBot\chromedriver-win64"
