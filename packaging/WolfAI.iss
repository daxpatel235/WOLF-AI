; Wolf AI Windows setup (Inno Setup 6.3+).
; Built by scripts\build.ps1:  iscc /DAppVersion=2.0.0 packaging\WolfAI.iss
; Installs per user by default (no admin prompt); the user can choose all users in the wizard.
; Keep AppId the same in every release so new versions upgrade the old one.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B0D3A6E2-5C1F-4E8A-9D47-3F2C8A1B6E90}
AppName=Wolf AI Code Debugger
AppVersion={#AppVersion}
AppVerName=Wolf AI Code Debugger {#AppVersion}
AppPublisher=Dax Patel
AppPublisherURL=https://github.com/daxpatel235/WOLF-AI
AppSupportURL=https://github.com/daxpatel235/WOLF-AI/issues
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Dax Patel
DefaultDirName={autopf}\Wolf AI
DefaultGroupName=Wolf AI
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=WolfAI-{#AppVersion}-x64-setup
SetupIconFile=icons\wolfai.ico
UninstallDisplayIcon={app}\WolfAI.exe
UninstallDisplayName=Wolf AI Code Debugger
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\WolfAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Wolf AI"; Filename: "{app}\WolfAI.exe"
Name: "{autodesktop}\Wolf AI"; Filename: "{app}\WolfAI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WolfAI.exe"; Description: "{cm:LaunchProgram,Wolf AI}"; Flags: nowait postinstall skipifsilent
