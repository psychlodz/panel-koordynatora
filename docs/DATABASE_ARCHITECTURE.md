# Architektura baz danych KOMPAS

## Podział odpowiedzialności

KOMPAS korzysta z trzech niezależnych źródeł danych:

| System | Rola | Zapis przez KOMPAS |
|---|---|---|
| Oracle / Eskulap | Źródło danych medycznych i organizacyjnych | Nie |
| PostgreSQL | Centralne dane KOMPAS w testach i produkcji | Tak |
| SQLite | Tryb developerski i lokalny fallback | Tak |

Oracle pozostaje dostępny wyłącznie przez `EskulapGateway`. PostgreSQL nie
zastępuje Oracle i nie służy do modyfikowania danych Eskulapa.

**Dane pacjenta są zawsze pobierane z Oracle przez Eskulap Gateway.**

### Oracle / Eskulap

Oracle jest systemem źródłowym i przechowuje:

- dane pacjenta,
- dane medyczne,
- wizyty,
- konsultacje,
- badania.

KOMPAS korzysta z tych danych wyłącznie do odczytu przez Eskulap Gateway.

### PostgreSQL

PostgreSQL jest centralną bazą danych procesowych KOMPAS i przechowuje:

- programy,
- ścieżki,
- epizody,
- zadania,
- użytkowników,
- role,
- przypisania jednostek organizacyjnych,
- konfigurację procesów KOMPAS.

Nie zawiera kartoteki pacjentów ani kopii danych osobowych.

```mermaid
flowchart TB
    O[("Oracle / Eskulap\nSystem of Record")]
    G["Eskulap Gateway\nwyłącznie SELECT"]
    UI["UI KOMPAS"]
    P[("PostgreSQL\ndane procesowe")]
    S[("SQLite\ndevelopment")]

    O --> G
    G -->|"aktualne dane pacjenta"| UI
    P -->|"programy, epizody, zadania"| UI
    UI -->|"zapis danych procesowych"| P
    S <-.->|"tryb developerski"| UI
```

## PostgreSQL

Centralna baza przechowuje programy, ścieżki, elementy procesu, zależności,
wyzwalacze, epizody, zadania, konta, role oraz przypisania jednostek.
Epizod zawiera wyłącznie `pacjent_id_eskulap`, który pozwala pobrać
aktualne dane pacjenta z Oracle. Schemat znajduje się w `db/postgres/`.

Warstwa `app/repositories/db_connection.py` potrafi utworzyć połączenie
SQLite lub PostgreSQL na podstawie sekcji `[kompas_database]`. Obecne
repozytoria danych KOMPAS korzystają wyłącznie z tej warstwy. Szczegóły
sterowników, placeholderów parametrów, zwracanych identyfikatorów i
różnic dialektu SQL nie przenikają do UI.

Repozytoria Oracle pozostają oddzielone od tego mechanizmu i nadal
korzystają z `db.py` poprzez Eskulap Gateway.

## Wybór silnika KOMPAS

Silnik jest wybierany w prywatnym `config.ini`.

SQLite:

```ini
[kompas_database]
engine=sqlite
sqlite_path=kompas.db
```

PostgreSQL:

```ini
[kompas_database]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=HASLO
```

Zmienna `KOMPAS_POSTGRES_DSN` ma pierwszeństwo przed DSN zapisanym w
pliku. Przed pierwszym uruchomieniem PostgreSQL należy wykonać skrypty
`db/postgres/001-005` zgodnie z instrukcją instalacji.

Test warstwy SQLite:

```text
python scripts/test_db_sqlite.py
```

Test zgodności oraz opcjonalny test serwera PostgreSQL:

```text
python scripts/test_db_postgres.py
```

Test integracyjny serwera uruchamia się po ustawieniu
`KOMPAS_TEST_POSTGRES_DSN`.

## SQLite

SQLite nadal jest domyślnym silnikiem developerskim. Dotychczasowy
`local_db.py`, baza `kompas.db` oraz istniejące repozytoria pozostają
niezmienione. Dzięki temu aktualna aplikacja działa lokalnie tak jak przed
dodaniem skryptów PostgreSQL.

Dotychczasowa kolumna SQLite `pk_epizody.pacjent_id` zawiera techniczny
identyfikator pacjenta z Eskulapa. Nie zawiera PESEL-u ani lokalnego
identyfikatora kartoteki KOMPAS. Przy przepięciu repozytoriów w DB-PG-2
odpowiada kolumnie PostgreSQL `pacjent_id_eskulap`.

## Dane pacjenta

PostgreSQL i SQLite nie utrzymują kopii PESEL-u, imienia, nazwiska, adresu,
telefonu, adresu e-mail ani innych danych identyfikacyjnych pacjenta.
Nie istnieje lokalny cache danych osobowych.

Model `Patient` jest obiektem DTO zwracanym przez Gateway i istnieje tylko
w pamięci procesu na czas obsługi żądania lub prezentacji danych. Nie jest
modelem trwałym i nie może być zapisywany przez repozytoria KOMPAS.

Szczegółowe zasady minimalizacji opisuje `docs/ARCHITECTURE/PRIVACY.md`.
