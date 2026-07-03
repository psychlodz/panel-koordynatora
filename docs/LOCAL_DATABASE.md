# Lokalna baza danych KOMPAS

Lokalna baza SQLite przechowuje wyłącznie dane Panelu Koordynatora/KOMPAS. Oracle/Eskulap pozostaje niezależnym źródłem danych tylko do odczytu.

## Lokalizacja

Baza nazywa się `kompas.db` i jest tworzona obok `plan_pracy.py`, a po zbudowaniu aplikacji — obok pliku wykonywalnego.

## Inicjalizacja

Moduł `local_db.py` udostępnia:

- `local_db_path()` — zwraca ścieżkę bazy;
- `create_local_connection()` — otwiera połączenie z obsługą kluczy obcych;
- `initialize_local_db()` — wykonuje `db/schema.sql`, a dla pustej bazy także `db/seed.sql`.

Inicjalizacja jest idempotentna. Seed nie jest wykonywany ponownie dla bazy, która posiada już tabele użytkownika. Obecny `seed.sql` dodaje 10 typów elementów, 13 podstawowych klocków procesu, program ADHD, ścieżkę podstawową oraz 9 elementów tej ścieżki.

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

### `pk_klocki`

Biblioteka klocków procesu używanych do budowania ścieżek. Przechowuje kod, nazwę, typ, opis, opcjonalną ikonę, aktywność i znaczniki czasu.

Klucz główny: `klocek_id`. Kod klocka jest unikalny.

### `pk_sciezka_elementy`

Elementy ścieżki zbudowane z klocków biblioteki. Każdy rekord wskazuje ścieżkę i klocek, zachowując nazwę używaną w konkretnej ścieżce, kolejność, liczebność, obowiązkowość, terminy, warunek aktywacji i opis organizacyjny.

Najważniejsze kolumny:

- `element_id` — klucz główny;
- `sciezka_id` — FK do `pk_sciezki.sciezka_id`;
- `klocek_id` — FK do `pk_klocki.klocek_id`;
- `lp` — kolejność elementu, unikalna w obrębie ścieżki;
- `nazwa_w_sciezce` — nazwa prezentowana w danej ścieżce;
- `min_liczba`, `max_liczba`, `czy_obowiazkowy`, `czy_wymaga_zlecenia`;
- `termin_liczba`, `termin_jednostka`, `termin_od`;
- `warunek_aktywacji`, `opis_organizacyjny`.

### `pk_sciezka_zaleznosci`

Skierowane zależności pomiędzy elementami jednej ścieżki. Relacja wskazuje element poprzedni (`element_od_id`) i następny (`element_do_id`). Typ jest ograniczony do `KOLEJNOSC` albo `WARUNEK`.

Klucze obce:

- `sciezka_id -> pk_sciezki.sciezka_id`;
- `element_od_id -> pk_sciezka_elementy.element_id`;
- `element_do_id -> pk_sciezka_elementy.element_id`.

Schemat zabrania relacji elementu do samego siebie oraz duplikatu tej samej pary. Repozytorium dodatkowo zapobiega cyklom.

### `pk_wyzwalacze`

Wyzwalacze aktywujące element ścieżki. Pole `element_id` wskazuje element aktywowany, a opcjonalne `trigger_element_id` element źródłowy.

Dozwolone typy:

- `START_EPIZODU`;
- `PO_ZAKONCZENIU`;
- `PO_ZLECENIU`;
- `PO_WYNIKU`;
- `RECZNIE`.

Częściowy indeks unikalny pozwala przypisać tylko jeden wyzwalacz `START_EPIZODU` do danego elementu. Repozytorium sprawdza również, czy wskazany element źródłowy należy do tej samej ścieżki.

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
