# Widoki Oracle dla KOMPAS

KOMPAS korzysta z danych Eskulapa wyłącznie w trybie odczytu. Dane
pacjentów, wizyt, konsultacji i badań nie są kopiowane do PostgreSQL. Baza
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
- `DATA_WIZYTY`,
- `DATA_PLANOWANA` — data planowanej wizyty; używana, gdy wizyta jest
  wpisana w Eskulapie, ale nie ma jeszcze daty realizacji,
- `PARAMETR_KOD` — kod rodzaju wizyty z `WP_PARAMETR`,
- `PARAMETR_NAZWA` — nazwa ze słownika `CG_REF_CODES`,
- `PARAMETR_CZY_AKTUALNE` — aktualność kodu słownikowego,
- `DECYZJA` — decyzja/status wizyty z Eskulapa, alias pola
  `RI_WIZYTY_W_PORADNIACH.WP_DECYZJA`.

Widok może udostępniać dodatkowe informacje, np. identyfikator wizyty,
status, jednostkę organizacyjną, personel i rodzaj świadczenia.
Synchronizacja epizodu filtruje wizyty po dacie efektywnej
`COALESCE(DATA_WIZYTY, DATA_PLANOWANA)`, żeby pokazywać także wizyty
zaplanowane, które nie mają jeszcze daty realizacji.

Wizyty kwalifikacyjne PKK są pobierane z `V_KOMPAS_WIZYTY`. Aplikacja
rozpoznaje je przez aktywne mapowania klocka `PKK_KWAL` w
`pk_mapowanie_wizyt`. Seed startowy mapuje `F18`, ale administrator może
dopisać kolejne kody bez zmiany aplikacji. Nie wymagają osobnego widoku
Oracle.

`RI_WIZYTY_W_PORADNIACH.WP_PARAMETR` przechowuje kod rodzaju wizyty.
Widok łączy go ze słownikiem `CG_REF_CODES` dla
`RV_DOMAIN = 'PARAMETRY'`: `RV_LOW_VALUE` jest kodem, `RV_MEANING` nazwą
wizyty/porady/sesji/terapii, a `RV_CZY_AKTUALNE` oznacza aktualność.

`RI_WIZYTY_W_PORADNIACH.WP_DECYZJA` jest zapisywane jako dane techniczne
powiązanej wizyty i wykorzystywane przez `EpisodeStateService`:

- `J` — pacjent obsłużony; przy dacie realizacji stan elementu to
  `ZREALIZOWANA`,
- `B` — wizyta anulowana; stan elementu to `ANULOWANA`.

### `ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT`

Pomocniczy, tylko do odczytu słownik rodzajów wizyt. Zwraca:

- `PARAMETR_KOD`,
- `PARAMETR_NAZWA`,
- `CZY_AKTUALNE`.

Docelowo będzie źródłem kodów mapowanych do klocków typu wizyta, sesja
i terapia.

### `ESK_RAPORTY.V_KOMPAS_KONSULTACJE`

Minimalny kontrakt kolumn:

- `PACJENT_ID`,
- `DATA_KONSULTACJI`,
- `DATA_PLANOWANA`,
- `DATA_PRZYJECIA`.

Synchronizacja epizodu filtruje konsultacje po dacie efektywnej
`COALESCE(DATA_PRZYJECIA, DATA_KONSULTACJI, DATA_PLANOWANA)`.
`DATA_PLANOWANA` jest wykorzystywana do pokazania konsultacji jako
zaplanowanej, gdy nie została jeszcze przyjęta/zrealizowana.

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
`SELECT` do pięciu widoków. Repozytorium:

- wykonuje tylko instrukcje `SELECT`,
- używa parametrów wiązanych dla danych użytkownika,
- nie wykonuje `INSERT`, `UPDATE`, `DELETE`, `MERGE` ani procedur,
- nie zapisuje rekordów pacjentów w PostgreSQL.

## Filtrowanie dat

`date_from` i `date_to` przyjmują obiekty `date`, `datetime` albo tekst
w formacie `RRRR-MM-DD`. Górna granica jest włączna dla całego dnia.
