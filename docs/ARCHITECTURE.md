# Architektura KOMPAS 1.0

Ten dokument opisuje aktualny stan aplikacji KOMPAS przygotowanej do wydania
1.0.

## Podział odpowiedzialności

```text
Eskulap / Oracle
        ↓
EskulapGateway
        ↓
Service
        ↓
Repository
        ↓
PostgreSQL
```

Warstwa UI korzysta z serwisów i repozytoriów. Nie wykonuje bezpośrednich
zapytań SQL do Oracle ani nie zna szczegółów połączenia z Eskulapem.

## Główne moduły

- `main.py` — punkt startowy aplikacji i launcher KOMPAS.
- `app/ui/` — okna i dialogi PySide6.
- `app/services/` — logika biznesowa, synchronizacja, stan epizodu,
  kontekst pracy i autoryzacja.
- `app/repositories/` — dostęp do danych KOMPAS w PostgreSQL.
- `app/gateway/` — integracja odczytowa z Eskulapem / Oracle.
- `app/models/` — modele DTO zwracane przez Gateway.
- `resources/styles/kompas.qss` — centralny styl interfejsu.
- `db/postgres/` — skrypty inicjalizujące bazę KOMPAS.
- `docs/` — dokumentacja instalacji, architektury i API.

## Bazy danych

KOMPAS korzysta z dwóch źródeł danych:

| System | Rola | Zapis przez KOMPAS |
|---|---|---|
| Oracle / Eskulap | Dane pacjenta, medyczne, wizyty, badania, konsultacje | Nie |
| PostgreSQL | Dane procesowe i konfiguracja KOMPAS | Tak |

PostgreSQL jest jedyną bazą procesową KOMPAS. Aplikacja nie tworzy lokalnej
bazy i nie przechowuje danych osobowych pacjenta poza identyfikatorem
`pacjent_id_eskulap`.

## Stan epizodu

Stan epizodu jest wyliczany centralnie przez `EpisodeStateService`.
Synchronizacja z Eskulapem zapisuje powiązania ze zdarzeniami, ale nie jest
źródłem statusów Dashboardu.

```text
EskulapGateway
        ↓
EpisodeSynchronizationService
        ↓
PostgreSQL
        ↓
EpisodeStateService
        ↓
Dashboard / Szczegóły epizodu
```

## Harmonogram pracy

Harmonogram pracy korzysta z przepływu:

```text
UI Harmonogramu
→ ScheduleService
→ EskulapGateway
→ ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ
  albo ESK_RAPORTY.V_KOMPAS_DOST_RODZ_WIZYT
→ Oracle / Eskulap
```

Widok Oracle jest tylko do odczytu. Popup kalendarza pokazuje nazwy rodzajów
wizyt z pola `RODZAJE_WIZYT`; kody pozostają danymi technicznymi.
Druga zakładka harmonogramu, „Dostępność rodzajów wizyt”, pobiera szczegóły
dostępności jednym zapytaniem i tworzy macierz miesięczną w aplikacji.

## Budowanie

- EXE: `build_exe.bat`
- Instalator Windows: `build_installer.bat`
- Spec PyInstaller: `plan_pracy.spec`
- Skrypt Inno Setup: `installer/KOMPAS.iss`

Wydanie 1.0 jest budowane jako:

```text
release/KOMPAS_1.0.0/
release/installers/KOMPAS_Setup_1.0.0.exe
```

## Dokumenty powiązane

- `docs/ARCHITECTURE/KOMPAS_MODULE_ARCHITECTURE.md`
- `docs/DATABASE_ARCHITECTURE.md`
- `docs/ARCHITECTURE/PRIVACY.md`
- `docs/API/ESKULAP_GATEWAY.md`
- `docs/ARCHITECTURE/BUSINESS_DICTIONARIES.md`
- `docs/RELEASE_NOTES_1.0.md`
