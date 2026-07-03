# Lokalna baza danych KOMPAS

Lokalna baza SQLite przechowuje wyłącznie dane Panelu Koordynatora/KOMPAS. Oracle/Eskulap pozostaje niezależnym źródłem danych tylko do odczytu.

## Lokalizacja

Baza nazywa się `kompas.db` i jest tworzona obok `plan_pracy.py`, a po zbudowaniu aplikacji — obok pliku wykonywalnego.

## Inicjalizacja

Moduł `local_db.py` udostępnia:

- `local_db_path()` — zwraca ścieżkę bazy;
- `create_local_connection()` — otwiera połączenie z obsługą kluczy obcych;
- `initialize_local_db()` — wykonuje `db/schema.sql`, a dla pustej bazy także `db/seed.sql`.

Inicjalizacja jest idempotentna. Seed nie jest wykonywany ponownie dla bazy, która posiada już tabele użytkownika. Obecny `seed.sql` dodaje 10 typów elementów, program ADHD, ścieżkę podstawową oraz 9 elementów tej ścieżki.

## Struktura tabel

### `pk_programy`

Definicje programów KOMPAS: kod, nazwa, wersja, opis, aktywność i okres obowiązywania.

Klucz główny: `program_id`. Kod programu jest unikalny.

### `pk_sciezki`

Ścieżki należące do programów. Para `program_id, kod` jest unikalna.

Klucz główny: `sciezka_id`. Klucz obcy: `program_id -> pk_programy.program_id`.

### `pk_typy_elementow`

Słownik typów elementów ścieżki.

Klucz główny: `typ_id`. Kod typu jest unikalny.

### `pk_sciezka_elementy`

Uporządkowane elementy ścieżki wraz z liczebnością, obowiązkowością, terminami, warunkami aktywacji i informacjami organizacyjnymi.

Klucz główny: `element_id`. Klucze obce:

- `sciezka_id -> pk_sciezki.sciezka_id`;
- `typ_id -> pk_typy_elementow.typ_id`.

### `pk_epizody`

Epizody pacjentów przypisane opcjonalnie do programu i ścieżki, ze statusem, koordynatorem i datami realizacji.

Klucz główny: `epizod_id`. Klucze obce:

- `program_id -> pk_programy.program_id`;
- `sciezka_id -> pk_sciezki.sciezka_id`.

### `pk_zadania`

Zadania epizodu powiązane opcjonalnie z elementem ścieżki. Przechowują status, terminy, źródło oraz identyfikatory Eskulapa używane wyłącznie jako referencje.

Klucz główny: `zadanie_id`. Klucze obce:

- `epizod_id -> pk_epizody.epizod_id`;
- `element_id -> pk_sciezka_elementy.element_id`.

## Indeksy

- `idx_pk_epizody_status` na `pk_epizody(status)`;
- `idx_pk_zadania_status` na `pk_zadania(status)`;
- `idx_pk_zadania_epizod` na `pk_zadania(epizod_id)`.

## Dystrybucja

Pliki `db/schema.sql` i `db/seed.sql` są dołączane do paczki PyInstallera. Plik `kompas.db` oraz jego pliki pomocnicze są ignorowane przez Git.

Obecny harmonogram nie inicjalizuje ani nie używa SQLite. Podłączenie edytora ścieżek będzie osobnym etapem.
