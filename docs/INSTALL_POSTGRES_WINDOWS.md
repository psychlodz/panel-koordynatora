# Instalacja PostgreSQL dla KOMPAS na Windows Server

## 1. Instalacja serwera

1. Pobierz wspieraną wersję PostgreSQL z oficjalnego instalatora dla Windows.
2. Uruchom instalator jako administrator.
3. Zainstaluj co najmniej PostgreSQL Server oraz Command Line Tools.
4. Ustaw silne, unikalne hasło konta administracyjnego `postgres`.
5. Pozostaw port `5432`, jeżeli nie koliduje z inną usługą.
6. Ustaw usługę PostgreSQL na automatyczne uruchamianie.

Skrypty KOMPAS należy wykonywać w `psql`, a nie w SQLite.

## 2. Utworzenie roli i bazy

Uruchom PowerShell jako administrator i przejdź do katalogu projektu.
Jeżeli `psql.exe` nie jest dostępny w `PATH`, użyj pełnej ścieżki, np.
`C:\Program Files\PostgreSQL\17\bin\psql.exe`.

Pierwszy skrypt wykonaj jako administrator PostgreSQL:

```powershell
psql -U postgres -d postgres -f db/postgres/001_create_database.sql
```

Skrypt utworzy rolę `kompas_app`, bezpiecznie zapyta o jej hasło i utworzy
bazę `kompas`. Polecenia tworzenia roli i bazy wymagają
uprawnień administratora PostgreSQL.

## 3. Schemat, dane, indeksy i uprawnienia

Wykonuj skrypty w kolejności numerów:

```powershell
psql -U kompas_app -d kompas -f db/postgres/003_schema.sql
psql -U kompas_app -d kompas -f db/postgres/004_seed.sql
psql -U kompas_app -d kompas -f db/postgres/005_indexes.sql
psql -U postgres -d kompas -f db/postgres/006_grants.sql
```

Pełna kolejność instalacji to:

1. `001_create_database.sql` — jako `postgres`, na bazie `postgres`,
2. `003_schema.sql` — jako `kompas_app`, na bazie `kompas`,
3. `004_seed.sql` — jako `kompas_app`, na bazie `kompas`,
4. `005_indexes.sql` — jako `kompas_app`, na bazie `kompas`,
5. `006_grants.sql` — jako `postgres`, na bazie `kompas`.

Plik `002_extensions.sql` pozostaje pustym punktem rozszerzeń i obecnie
nie wymaga wykonania.

Skrypt `006_grants.sql` należy uruchomić na bazie `kompas` jako użytkownik
`postgres`. Nadaje `kompas_app` dostęp do istniejących tabel i sekwencji
oraz ustawia uprawnienia domyślne dla przyszłych obiektów.

Każdy skrypt ma włączone zatrzymanie po pierwszym błędzie. Nie przechodź
do następnego kroku, dopóki bieżący skrypt nie zakończy się poprawnie.

## 4. Dostęp sieciowy

Pliki konfiguracyjne znajdują się zwykle w katalogu danych instancji, np.
`C:\Program Files\PostgreSQL\17\data`.

W `postgresql.conf` ustaw adresy, na których serwer ma nasłuchiwać:

```conf
listen_addresses = '*'
port = 5432
```

Bezpieczniej jest podać konkretny adres IP serwera zamiast `*`, jeśli
infrastruktura na to pozwala.

W `pg_hba.conf` dodaj wyłącznie sieć klientów KOMPAS, przykładowo:

```conf
host    kompas    kompas_app    192.168.10.0/24    scram-sha-256
```

Nie używaj `0.0.0.0/0`. Po zmianie konfiguracji uruchom ponownie usługę
PostgreSQL.

## 5. Zapora Windows

Otwórz port tylko dla zaufanej sieci klientów:

```powershell
New-NetFirewallRule `
  -DisplayName "PostgreSQL KOMPAS 5432" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 5432 `
  -RemoteAddress 192.168.10.0/24 `
  -Action Allow
```

Dostosuj `RemoteAddress` do rzeczywistej podsieci placówki.

## 6. Konfiguracja aplikacji

Na każdej stacji KOMPAS zainstaluj zależności aplikacji:

```powershell
python -m pip install -r requirements.txt
```

W prywatnym `config.ini` ustaw:

```ini
[kompas_database]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=HASLO
```

Alternatywnie cały DSN umieść w zmiennej `KOMPAS_POSTGRES_DSN`. Ma ona
pierwszeństwo przed wartością z pliku.

Dla dotychczasowego trybu lokalnego pozostaw:

```ini
[kompas_database]
engine=sqlite
sqlite_path=kompas.db
```

Brak sekcji `[kompas_database]` również oznacza domyślny tryb SQLite.

## 7. Test z serwera i klienta

Na serwerze:

```powershell
psql -U kompas_app -h localhost -d kompas -c "SELECT current_database();"
```

Na stacji klienckiej:

```powershell
psql -U kompas_app -h SERVER -p 5432 -d kompas -c "SELECT now();"
```

Można także sprawdzić utworzone tabele:

```powershell
psql -U kompas_app -h SERVER -d kompas `
  -c "\dt pk_*"
```

Po wykonaniu `006_grants.sql` sprawdź operacje aplikacyjne:

```powershell
python scripts/test_db_postgres.py
```

Test korzysta z DSN ustawionego w `KOMPAS_TEST_POSTGRES_DSN`.

## 8. Kopia zapasowa

Przykładowy backup w formacie archiwum:

```powershell
pg_dump -U postgres -h localhost -d kompas -Fc `
  -f D:\Backup\kompas_2026-07-04.dump
```

Backup zawiera dane procesowe KOMPAS i nadal wymaga ochrony dostępu oraz
bezpiecznej retencji.

## 9. Odtwarzanie

Odtworzenie archiwum do pustej bazy:

```powershell
createdb -U postgres -O kompas_app kompas_restore
pg_restore -U postgres -d kompas_restore `
  --no-owner --role=kompas_app D:\Backup\kompas_2026-07-04.dump
```

Dla kopii tekstowej SQL:

```powershell
psql -U postgres -d kompas_restore -f D:\Backup\kompas.sql
```

Po odtworzeniu sprawdź logi, liczbę tabel i przykładowe rekordy procesowe.
