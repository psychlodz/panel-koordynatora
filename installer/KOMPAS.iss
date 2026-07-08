#define MyAppName "KOMPAS"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "KOMPAS"
#define MyAppExeName "KOMPAS.exe"
#define ProjectRoot ".."
#define ReleaseDir ProjectRoot + "\release\KOMPAS_" + MyAppVersion

[Setup]
AppId={{A2AB8B65-41E6-4AF1-A672-25B3B84B6D61}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#ProjectRoot}\release\installers
OutputBaseFilename=KOMPAS_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupLogging=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Skróty:"; Flags: checkedonce

[Dirs]
Name: "{commonappdata}\KOMPAS"
Name: "{commonappdata}\KOMPAS\config"
Name: "{commonappdata}\KOMPAS\logs"
Name: "{app}\logs"

[Files]
Source: "{#ReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config.ini,kompas.db,*.tmp,*.bak,*.pyc,__pycache__\*,.git\*,.idea\*"

[Icons]
Name: "{group}\KOMPAS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Odinstaluj KOMPAS"; Filename: "{uninstallexe}"
Name: "{commondesktop}\KOMPAS"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom KOMPAS po zakończeniu instalacji"; Flags: nowait postinstall skipifsilent

[Code]
var
  PgPage: TInputQueryWizardPage;

function ValueOrDefault(Value: String; DefaultValue: String): String;
begin
  if Trim(Value) = '' then
    Result := DefaultValue
  else
    Result := Trim(Value);
end;

procedure InitializeWizard;
begin
  PgPage := CreateInputQueryPage(
    wpSelectDir,
    'Konfiguracja PostgreSQL',
    'Podaj parametry centralnej bazy KOMPAS.',
    'Instalator utworzy plik config.ini, jeżeli go jeszcze nie ma. Hasło nie zostanie zapisane automatycznie; uzupełnij je ręcznie po instalacji.'
  );
  PgPage.Add('Adres serwera PostgreSQL:', False);
  PgPage.Add('Port:', False);
  PgPage.Add('Nazwa bazy:', False);
  PgPage.Add('Użytkownik:', False);
  PgPage.Add('Hasło (nie zostanie zapisane automatycznie):', True);

  PgPage.Values[0] := 'SERVER';
  PgPage.Values[1] := '5432';
  PgPage.Values[2] := 'kompas';
  PgPage.Values[3] := 'kompas_app';
  PgPage.Values[4] := '';
end;

function BuildConfigText: String;
var
  PgHost: String;
  PgPort: String;
  PgDb: String;
  PgUser: String;
begin
  PgHost := ValueOrDefault(PgPage.Values[0], 'SERVER');
  PgPort := ValueOrDefault(PgPage.Values[1], '5432');
  PgDb := ValueOrDefault(PgPage.Values[2], 'kompas');
  PgUser := ValueOrDefault(PgPage.Values[3], 'kompas_app');

  Result :=
    '[database]' + #13#10 +
    'user=YOUR_ORACLE_USER' + #13#10 +
    'password=YOUR_ORACLE_PASSWORD' + #13#10 +
    'dsn=HOST:PORT/SERVICE_NAME' + #13#10 +
    #13#10 +
    '[application]' + #13#10 +
    'default_jo_id=249' + #13#10 +
    'default_months=3' + #13#10 +
    'slot_minutes=180' + #13#10 +
    'hour_start=7' + #13#10 +
    'hour_end=22' + #13#10 +
    'view_name=ESK_RAPORTY.V_PLAN_PRACY_KALENDARZ' + #13#10 +
    #13#10 +
    '[kompas_db]' + #13#10 +
    'engine=postgres' + #13#10 +
    'postgres_dsn=host=' + PgHost + ' port=' + PgPort + ' dbname=' + PgDb +
    ' user=' + PgUser + ' password=UZUPELNIJ_RECZNIE' + #13#10;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  NewConfigPath: String;
  ConfigText: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigPath := ExpandConstant('{app}\config.ini');
    NewConfigPath := ExpandConstant('{app}\config.ini.new');
    ConfigText := BuildConfigText;

    if FileExists(ConfigPath) then
    begin
      SaveStringToFile(NewConfigPath, ConfigText, False);
      Log('Istniejący config.ini zachowany. Nowy wzorzec zapisano jako config.ini.new.');
    end
    else
    begin
      SaveStringToFile(ConfigPath, ConfigText, False);
      Log('Utworzono config.ini.');
    end;
  end;
end;
