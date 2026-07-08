# Instalacja klienta KOMPAS na Windows

Ten dokument opisuje instalację aplikacji klienckiej KOMPAS z pakietu
`KOMPAS_Setup_<wersja>.exe`.

## Wymagania systemowe

- Windows 10/11 x64 albo Windows Server x64.
- Dostęp sieciowy do centralnej bazy PostgreSQL KOMPAS.
- Dostęp sieciowy do Oracle/Eskulap, jeżeli stanowisko ma pobierać dane
  medyczne i dane pacjentów.
- Konto PostgreSQL aplikacji, np. `kompas_app`.
- Konto Oracle/Eskulap tylko do odczytu.
- Uprawnienia administratora lokalnego do instalacji w `C:\Program Files`.

## Instalacja

1. Uruchom `KOMPAS_Setup_<wersja>.exe`.
2. Pozostaw domyślny katalog instalacji:
   `C:\Program Files\KOMPAS`.
3. Na stronie konfiguracji PostgreSQL wpisz:
   - adres serwera,
   - port, zwykle `5432`,
   - nazwę bazy, zwykle `kompas`,
   - użytkownika, zwykle `kompas_app`.
4. Hasło PostgreSQL nie jest zapisywane automatycznie przez instalator.
   Po instalacji uzupełnij je ręcznie w `config.ini`.
5. Wybierz, czy utworzyć skrót na pulpicie.
6. Opcjonalnie zaznacz uruchomienie KOMPAS po zakończeniu instalacji.

Instalator tworzy skróty:

- menu Start: `KOMPAS`;
- pulpit: `KOMPAS`, jeśli wybrano odpowiednią opcję.

## Lokalizacja plików

Domyślna instalacja:

```text
C:\Program Files\KOMPAS\
├── KOMPAS.exe
├── config.ini
├── config.example.ini
├── VERSION.txt
├── resources\
│   └── styles\
│       └── kompas.qss
└── logs\
```

Instalator tworzy też katalogi systemowe:

```text
C:\ProgramData\KOMPAS\
├── config\
└── logs\
```

Aktualna aplikacja korzysta z `config.ini` w katalogu instalacji.

## Konfiguracja PostgreSQL

Otwórz:

```text
C:\Program Files\KOMPAS\config.ini
```

Sekcja PostgreSQL powinna wyglądać podobnie:

```ini
[kompas_db]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=UZUPELNIJ_RECZNIE
```

Uzupełnij:

- `host`,
- `port`,
- `dbname`,
- `user`,
- `password`.

Hasło nie powinno być wpisywane do plików instalatora ani repozytorium.

## Konfiguracja Oracle / Eskulap

W tym samym pliku uzupełnij sekcję:

```ini
[database]
user=YOUR_ORACLE_USER
password=YOUR_ORACLE_PASSWORD
dsn=HOST:PORT/SERVICE_NAME
```

Konto Oracle powinno mieć wyłącznie uprawnienia odczytu do widoków KOMPAS.
KOMPAS nie zapisuje danych do Oracle.

## Test uruchomienia

1. Uruchom KOMPAS z menu Start.
2. Sprawdź, czy pojawia się okno logowania albo okno główne aplikacji.
3. Zaloguj się kontem aplikacyjnym.
4. Otwórz moduł Dashboard albo Programy.
5. Jeżeli moduł wymaga danych Eskulapa, sprawdź połączenie przez
   Administracja → Ustawienia systemu → Diagnostyka.

## Aktualizacja i config.ini

Instalator nie nadpisuje istniejącego `config.ini`.

Jeżeli `config.ini` już istnieje, nowy wzorzec zostanie zapisany jako:

```text
C:\Program Files\KOMPAS\config.ini.new
```

Porównaj wtedy ręcznie `config.ini.new` z obecnym `config.ini`.

## Typowe błędy

### Brak połączenia PostgreSQL

Objaw:

```text
Brak połączenia z centralną bazą KOMPAS PostgreSQL. Sprawdź konfigurację.
```

Sprawdź:

- adres i port PostgreSQL;
- nazwę bazy;
- użytkownika i hasło;
- reguły zapory Windows;
- `pg_hba.conf` na serwerze;
- czy baza `kompas` działa.

### Błędny config.ini

Sprawdź, czy plik zawiera sekcje:

```ini
[database]
[application]
[kompas_db]
```

Sprawdź też, czy `engine=postgres`.

### Brak dostępu do Oracle

Sprawdź:

- `dsn` w sekcji `[database]`;
- login i hasło Oracle;
- dostęp sieciowy do serwera Oracle;
- uprawnienia konta do widoków `ESK_RAPORTY.V_KOMPAS_*`.

### Brak uprawnień do katalogu Program Files

Jeżeli nie można zapisać `config.ini`, uruchom edytor jako administrator
albo poproś administratora systemu o zmianę konfiguracji.

Nie zapisuj danych pacjentów, eksportów ani plików roboczych w katalogu
instalacji aplikacji.
