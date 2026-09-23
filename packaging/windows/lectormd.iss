; Instalador de lectorMD para Windows (Inno Setup 6).
; Lo invoca build.ps1:  ISCC /DAppVersion=2.0.0 packaging\windows\lectormd.iss
; Las rutas son relativas a esta carpeta.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "lectorMD"
#define AppExe "lectorMD.exe"

[Setup]
; Identificador fijo: permite actualizar y desinstalar versiones anteriores.
AppId={{7E3C2F9A-4B1D-4E8A-9C6F-2A5B8D1E0F47}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Se instala sin permisos de administrador (solo para el usuario actual),
; salvo que se elija "para todos los usuarios" en el diálogo.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename={#AppName}-{#AppVersion}-windows-setup
SetupIconFile=..\iconos\lectormd.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
es.AsociarMD=Añadir {#AppName} a «Abrir con» para archivos .md
en.AsociarMD=Add {#AppName} to "Open with" for .md files
es.Asociaciones=Archivos:
en.Asociaciones=Files:

[Tasks]
Name: "escritorio"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "asociar"; Description: "{cm:AsociarMD}"; GroupDescription: "{cm:Asociaciones}"

[Files]
Source: "..\..\dist\lectorMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: escritorio

[Registry]
; Tipo de documento propio (ProgID).
Root: HKA; Subkey: "Software\Classes\lectorMD.md"; ValueType: string; ValueName: ""; ValueData: "Documento Markdown"; Flags: uninsdeletekey; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\lectorMD.md\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\lectorMD.md\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: asociar
; Windows 10/11 no deja que un instalador imponga la aplicación por defecto:
; se registra en «Abrir con» y el usuario la elige una vez.
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "lectorMD.md"; ValueData: ""; Flags: uninsdeletevalue; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "lectorMD.md"; ValueData: ""; Flags: uninsdeletevalue; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".markdown"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
