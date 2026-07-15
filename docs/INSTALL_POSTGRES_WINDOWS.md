# Instalacja PostgreSQL dla KOMPAS na Windows Server

## 1. Instalacja serwera

1. Pobierz wspieraną wersję PostgreSQL z oficjalnego instalatora dla Windows.
2. Uruchom instalator jako administrator.
3. Zainstaluj co najmniej PostgreSQL Server oraz Command Line Tools.
4. Ustaw silne, unikalne hasło konta administracyjnego `postgres`.
5. Pozostaw port `5432`, jeżeli nie koliduje z inną usługą.
6. Ustaw usługę PostgreSQL na automatyczne uruchamianie.

Skrypty KOMPAS należy wykonywać w `psql`.

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

Zmiany modeli ADM-DICT-3, ADM-DICT-4 i ADM-DICT-5 nie posiadają migracji danych.
Dla bazy testowej należy usunąć dotychczasową bazę `kompas`, utworzyć ją
ponownie i wykonać komplet aktualnych skryptów. ADM-DICT-4 dodaje
`pk_klocki.kolor_tekstu` oraz tabelę `pk_mapowanie_wizyt`. Nie uruchamiaj
nowego schematu na bazie zawierającej starszy model.

ADM-DICT-5 usuwa mechanizm grup klocków. Typ klocka jest podstawowym i jedynym
mechanizmem klasyfikacji elementów procesu w KOMPAS.

Przykład odtworzenia bazy testowej jako `postgres`:

```powershell
psql -U postgres -d postgres `
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='kompas' AND pid <> pg_backend_pid();"
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS kompas;"
psql -U postgres -d postgres -f db/postgres/001_create_database.sql
```

Operacja `DROP DATABASE` bezpowrotnie usuwa dane. Wykonaj ją wyłącznie dla
bazy testowej albo po przygotowaniu i sprawdzeniu kopii zapasowej.

Wykonuj skrypty w kolejności numerów:

```powershell
psql -U kompas_app -d kompas -f db/postgres/003_schema.sql
psql -U kompas_app -d kompas -f db/postgres/004_seed.sql
psql -U kompas_app -d kompas -f db/postgres/005_indexes.sql
psql -U postgres -d kompas -f db/postgres/006_grants.sql
psql -U postgres -d kompas -f db/postgres/007_episode_auto_duplicates.sql
psql -U postgres -d kompas -f db/postgres/008_episode_manual_planning.sql
```

Pełna kolejność instalacji to:

1. `001_create_database.sql` — jako `postgres`, na bazie `postgres`,
2. `003_schema.sql` — jako `kompas_app`, na bazie `kompas`,
3. `004_seed.sql` — jako `kompas_app`, na bazie `kompas`,
4. `005_indexes.sql` — jako `kompas_app`, na bazie `kompas`,
5. `006_grants.sql` — jako `postgres`, na bazie `kompas`,
6. `007_episode_auto_duplicates.sql` — jako `postgres`, na bazie `kompas`,
7. `008_episode_manual_planning.sql` — jako `postgres`, na bazie `kompas`.

Plik `002_extensions.sql` pozostaje pustym punktem rozszerzeń i obecnie
nie wymaga wykonania.

Skrypt `006_grants.sql` należy uruchomić na bazie `kompas` jako użytkownik
`postgres`. Nadaje `kompas_app` dostęp do istniejących tabel i sekwencji
oraz ustawia uprawnienia domyślne dla przyszłych obiektów.

Skrypt `007_episode_auto_duplicates.sql` aktualizuje constrainty
`pk_epizod_elementy` i `pk_epizod_elementy_historia`, aby KOMPAS mógł
zapisywać automatyczne powielenia elementów epizodu dla konsultacji
specjalistycznych i badań obrazowych. Ten sam skrypt tworzy też indeks
`uq_pk_zadania_eskulap_event`, który zabezpiecza przed przypisaniem jednego
zdarzenia Eskulapa do wielu zadań KOMPAS.

Skrypt `008_episode_manual_planning.sql` dodaje lokalne pola planowania
terminów KOMPAS dla konsultacji i badań obrazowych oraz informacyjne pola
dat planowanych z Eskulapa. Data planowana z Eskulapa nie ustawia statusu
`ZAPLANOWANA`; robi to dopiero termin zapisany ręcznie w KOMPAS.

Każdy skrypt ma włączone zatrzymanie po pierwszym błędzie. Nie przechodź
do następnego kroku, dopóki bieżący skrypt nie zakończy się poprawnie.

## 4. Kodowanie UTF-8 i polskie znaki

Baza KOMPAS musi używać kodowania `UTF8`. Przed uruchomieniem `psql`
w PowerShell ustaw stronę kodową konsoli oraz kodowanie klienta:

```powershell
chcp 65001
$env:PGCLIENTENCODING = "UTF8"
```

Skrypty `db/postgres/001-008` wykonują dodatkowo:

```sql
SET client_encoding = 'UTF8';
```

`001_create_database.sql` tworzy bazę z `ENCODING 'UTF8'`. Ustawienia
`lc_collate` i `lc_ctype` zależą od lokalizacji wybranej podczas instalacji
PostgreSQL na Windows. Powinny być zgodne z instalacją serwera i wymaganiami
sortowania placówki. Ich zmiana wymaga ponownego utworzenia bazy.

Sprawdzenie parametrów bazy:

```sql
SELECT datname, pg_encoding_to_char(encoding), datcollate, datctype
FROM pg_database
WHERE datname = 'kompas';
```

Sprawdzenie kodowania bieżącego połączenia:

```sql
SHOW client_encoding;
```

Kontrola nazw programów, ścieżek, klocków i elementów:

```powershell
python scripts/check_polish_chars.py
```

Skrypt kończy się kodem błędu, jeśli baza lub połączenie nie używa UTF-8
albo dane zawierają podejrzane sekwencje `Å`, `Ä`, `Ã`, `Â`, `Ĺ` lub `Ă`.

Opcjonalna naprawa danych słownikowych wymaga wcześniej wykonanej kopii
zapasowej i jawnego parametru:

```powershell
python scripts/fix_polish_chars.py --apply
```

Skrypt najpierw wypisuje wszystkie proponowane zmiany, modyfikuje wyłącznie
tabele programowe i słownikowe KOMPAS oraz nie łączy się z Oracle.

## 5. Dostęp sieciowy

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

## 6. Zapora Windows

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

## 7. Konfiguracja aplikacji

Na każdej stacji KOMPAS zainstaluj zależności aplikacji:

```powershell
python -m pip install -r requirements.txt
```

W prywatnym `config.ini` ustaw jedyną wspieraną bazę procesową:

```ini
[kompas_db]
engine=postgres
postgres_dsn=host=SERVER port=5432 dbname=kompas user=kompas_app password=HASLO
```

Alternatywnie cały DSN umieść w zmiennej `KOMPAS_POSTGRES_DSN`. Ma ona
pierwszeństwo przed wartością z pliku.

Brak poprawnego DSN PostgreSQL zatrzymuje dostęp do modułów KOMPAS.

## 8. Test z serwera i klienta

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

## 9. Kopia zapasowa

Przykładowy backup w formacie archiwum:

```powershell
pg_dump -U postgres -h localhost -d kompas -Fc `
  -f D:\Backup\kompas_2026-07-04.dump
```

Backup zawiera dane procesowe KOMPAS i nadal wymaga ochrony dostępu oraz
bezpiecznej retencji.

## 10. Odtwarzanie

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
## Aktualizacja ADM-VISIT-DICT-1

ADM-VISIT-DICT-1 dodaje lokalny słownik rodzajów wizyt Eskulapa
`pk_rodzaje_wizyt_eskulap` oraz przebudowuje `pk_mapowanie_wizyt` tak, aby
mapowania wskazywały rekord słownika, a nie tekstowy kod. Dla baz testowych
zalecane jest odtworzenie bazy od zera aktualnymi skryptami:

```powershell
psql -U postgres -d postgres -f db/postgres/001_create_database.sql
psql -U kompas_app -d kompas -f db/postgres/003_schema.sql
psql -U kompas_app -d kompas -f db/postgres/004_seed.sql
psql -U kompas_app -d kompas -f db/postgres/005_indexes.sql
psql -U postgres -d kompas -f db/postgres/006_grants.sql
psql -U postgres -d kompas -f db/postgres/007_episode_auto_duplicates.sql
psql -U postgres -d kompas -f db/postgres/008_episode_manual_planning.sql
```

Po instalacji wykonaj synchronizację słownika w aplikacji:
`Administracja -> Ustawienia systemu -> Integracja Eskulap -> Rodzaje wizyt`
i kliknij „Synchronizuj z Eskulapem”.
