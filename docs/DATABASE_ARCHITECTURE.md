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

## PostgreSQL

Centralna baza przechowuje programy, ścieżki, elementy procesu, zależności,
wyzwalacze, epizody, zadania, konta, role oraz przypisania jednostek.
Schemat znajduje się w `db/postgres/`.

Warstwa `app/repositories/db_connection.py` potrafi utworzyć połączenie
SQLite lub PostgreSQL na podstawie sekcji `[kompas_database]`. Obecne
repozytoria nie zostały jeszcze przepięte na tę warstwę; nastąpi to w
osobnym etapie migracji.

## SQLite

SQLite nadal jest domyślnym silnikiem developerskim. Dotychczasowy
`local_db.py`, baza `kompas.db` oraz istniejące repozytoria pozostają
niezmienione. Dzięki temu aktualna aplikacja działa lokalnie tak jak przed
dodaniem skryptów PostgreSQL.

## Dane pacjenta i szyfrowanie

Tabela `pk_patient_cache` identyfikuje osobę przez techniczny identyfikator
Eskulapa. Pola PESEL, imię i nazwisko są typu `bytea` i mają być zapisywane
wyłącznie poprzez szyfrowanie `pgp_sym_encrypt`.

Funkcje:

- `kompas_encrypt_patient_text(text)` — szyfruje wartość algorytmem AES-256,
- `kompas_decrypt_patient_text(bytea)` — odszyfrowuje wartość.

Funkcje pobierają klucz z ustawienia sesji:

```sql
current_setting('kompas.data_key')
```

Aplikacja pobiera sekret ze zmiennej `KOMPAS_DATA_KEY` i ustawia go przez
`set_config()` natychmiast po połączeniu. Klucz nie jest przechowywany w
bazie, `config.ini`, kodzie ani repozytorium.

Przykład użycia po ustawieniu klucza sesji:

```sql
INSERT INTO pk_patient_cache(
    pacjent_id_eskulap,
    pesel_enc,
    imie_enc,
    nazwisko_enc
)
VALUES (
    '12345',
    kompas_encrypt_patient_text('00000000000'),
    kompas_encrypt_patient_text('Jan'),
    kompas_encrypt_patient_text('Kowalski')
);
```

Dostęp do funkcji odszyfrowującej powinien być ograniczony do konta
aplikacyjnego i kontrolowany przez warstwę usług KOMPAS.

