# KOMPAS

KOMPAS jest desktopową platformą koordynacji programów
diagnostyczno-terapeutycznych. Aplikacja wspiera pracę koordynatora:
dashboard epizodów, pacjentów w programach, harmonogram pracy, programy,
ścieżki oraz administrację ustawieniami systemu.

## Architektura danych

- **Oracle / Eskulap** — system źródłowy danych pacjenta, danych medycznych,
  wizyt, badań, konsultacji i danych referencyjnych. KOMPAS korzysta z niego
  wyłącznie do odczytu przez `EskulapGateway`.
- **PostgreSQL** — jedyna baza procesowa i konfiguracyjna KOMPAS.

KOMPAS nie utrzymuje lokalnej kopii danych osobowych pacjenta. W bazie
procesowej zapisywany jest wyłącznie techniczny identyfikator pacjenta
z Eskulapa.

Konfiguracja bazy KOMPAS:

```ini
[kompas_db]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=HASLO
```

## Architektura modułów KOMPAS 1.0

```text
KOMPAS
├── Dashboard
├── Pacjenci / Epizody
├── Harmonogram
├── Programy
├── Ścieżki
├── Administracja
│   └── Ustawienia systemu
├── Gateway Eskulap
└── Pomoc
```

Szczegółowy opis znajduje się w
[architekturze modułów](docs/ARCHITECTURE/KOMPAS_MODULE_ARCHITECTURE.md).
Decyzję formalizuje
[ADR-001](docs/ADR/ADR-001-module-architecture-freeze.md).

## Najważniejsze zasady 1.0

- UI nie odwołuje się bezpośrednio do Oracle.
- Dane Eskulapa pobierane są przez `EskulapGateway`.
- Dane procesowe zapisywane są w PostgreSQL.
- Stan epizodu wylicza centralnie `EpisodeStateService`.
- Synchronizacja z Eskulapem jest jednokierunkowa i nie zapisuje danych do
  Oracle.
- Style interfejsu są centralizowane w QSS.

## Uruchomienie developerskie

1. Przygotuj `config.ini` na podstawie `config.example.ini`.
2. Upewnij się, że PostgreSQL KOMPAS jest dostępny.
3. Uruchom:

```text
python main.py
```

## Testy podstawowe

```text
python scripts/test_db_postgres.py
python scripts/test_business_dictionaries.py
python scripts/test_episode_synchronization.py
python scripts/test_episode_state_service.py
python scripts/test_episode_details_presenter.py
python scripts/test_schedule_data_source.py
```

Testy wymagające Oracle lub testowego PostgreSQL mogą wymagać lokalnej
konfiguracji połączeń.

## Budowanie wydania

```text
build_exe.bat
```

Wynik:

```text
release/KOMPAS_1.0.0/
```

## Budowanie instalatora Windows

```text
build_installer.bat
```

Wynik:

```text
release/installers/KOMPAS_Setup_1.0.0.exe
```

Szczegóły:

- [budowanie instalatora](docs/BUILD_INSTALLER.md),
- [instalacja klienta Windows](docs/INSTALL_CLIENT_WINDOWS.md),
- [instalacja PostgreSQL](docs/INSTALL_POSTGRES_WINDOWS.md).
