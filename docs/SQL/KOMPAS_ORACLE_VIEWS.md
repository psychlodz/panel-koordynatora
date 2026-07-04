# Widoki Oracle dla KOMPAS

KOMPAS korzysta z danych Eskulapa wyłącznie w trybie odczytu. Dane
pacjentów, wizyt, konsultacji i badań nie są kopiowane do SQLite. Lokalna baza
przechowuje jedynie identyfikator `PACJENT_ID` przypisany do epizodu.

Definicje instalacyjne znajdują się w pliku
[`kompas_oracle_views.sql`](kompas_oracle_views.sql). Skrypt powinien
wykonać administrator Oracle, a nie konto aplikacyjne KOMPAS.

## Wymagane widoki

### `ESK_RAPORTY.V_KOMPAS_PACJENCI`

Minimalny kontrakt kolumn:

- `PACJENT_ID` — stabilny identyfikator pacjenta w Eskulapie,
- `PESEL`,
- `IMIE`,
- `NAZWISKO`,
- `DATA_URODZENIA`.

Repozytorium wyszukuje pacjentów po fragmencie `NAZWISKO` albo `PESEL`.

### `ESK_RAPORTY.V_KOMPAS_WIZYTY`

Minimalny kontrakt kolumn:

- `PACJENT_ID`,
- `DATA_WIZYTY`.

Widok może udostępniać dodatkowe informacje, np. identyfikator wizyty,
status, jednostkę organizacyjną, personel i rodzaj świadczenia.

Wizyty kwalifikacyjne PKK są pobierane z `V_KOMPAS_WIZYTY`. Aplikacja
filtruje je po typie wizyty, symbolu lub nazwie poradni oraz opisie.
Nie wymagają osobnego widoku Oracle.

### `ESK_RAPORTY.V_KOMPAS_KONSULTACJE`

Minimalny kontrakt kolumn:

- `PACJENT_ID`,
- `DATA_KONSULTACJI`.

Źródłem widoku jest `RI_OWNER.OD_KONSULTACJE`.

Po zmianie definicji SQL administrator musi ręcznie wykonać
`CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_KONSULTACJE` w Oracle.
Sama aktualizacja pliku w projekcie nie zmienia widoku w bazie.

### `ESK_RAPORTY.V_KOMPAS_BADANIA`

Minimalny kontrakt kolumn:

- `PACJENT_ID`,
- `DATA_SKIEROWANIA`,
- `DATA_PLANOWANA_WYKONANIA`,
- `DATA_ZAPLANOWANA`,
- `DATA_POBRANIA`,
- `DATA_REALIZACJI`.

Źródłem widoku jest `RI_OWNER.OD_SKIEROWANIA_NA_BADANIA`. Nazwa, symbol
i kod badania mogą zostać uzupełnione ze słownika `LAB_OWNER.L_BADANIA`.
Widok nie korzysta z ogólnego źródła e-skierowań.

## Zasady dostępu

Konto skonfigurowane w `config.ini` powinno mieć wyłącznie uprawnienie
`SELECT` do czterech widoków. Repozytorium:

- wykonuje tylko instrukcje `SELECT`,
- używa parametrów wiązanych dla danych użytkownika,
- nie wykonuje `INSERT`, `UPDATE`, `DELETE`, `MERGE` ani procedur,
- nie zapisuje rekordów pacjentów w SQLite.

## Filtrowanie dat

`date_from` i `date_to` przyjmują obiekty `date`, `datetime` albo tekst
w formacie `RRRR-MM-DD`. Górna granica jest włączna dla całego dnia.
