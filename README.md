# KOMPAS

KOMPAS jest platformą koordynacji programów
diagnostyczno-terapeutycznych.

Oracle/Eskulap jest systemem źródłowym danych pacjenta i danych medycznych.
KOMPAS zarządza programami, ścieżkami, epizodami, zadaniami oraz
konfiguracją procesu.

## Bazy danych

- **Oracle / Eskulap** — system źródłowy danych pacjenta i danych
  medycznych; KOMPAS korzysta z niego wyłącznie do odczytu przez
  `EskulapGateway`.
- **PostgreSQL** — jedyna baza procesowa i konfiguracyjna KOMPAS.
- **SQLite** — historyczny, niewspierany mechanizm zachowany wyłącznie
  w katalogu `db/sqlite_deprecated/`; aplikacja go nie uruchamia i nie
  tworzy pliku `kompas.db`.

Konfiguracja bazy KOMPAS wymaga sekcji:

```ini
[kompas_db]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=HASLO
```

## Architektura modułów KOMPAS

Struktura modułów KOMPAS 1.0 została zatwierdzona i zamrożona jako punkt
odniesienia dla kolejnych sprintów:

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

Nowy moduł może powstać tylko wtedy, gdy nie mieści się logicznie w żadnym
z zatwierdzonych modułów.

## Uruchomienie

Konfigurację połączeń należy przygotować na podstawie
`config.example.ini`, a aplikację developerską uruchomić poleceniem:

```text
python main.py
```

Budowanie wydania:

```text
build_exe.bat
```
