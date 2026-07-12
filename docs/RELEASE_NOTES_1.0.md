# KOMPAS 1.0 — release notes

Data przygotowania: 2026-07-12

## Charakter wydania

KOMPAS 1.0 jest pierwszym stabilnym wydaniem aplikacji jako platformy
koordynacji programów diagnostyczno-terapeutycznych. Wydanie porządkuje
architekturę wokół PostgreSQL, EskulapGateway i centralnego stanu epizodu.

## Najważniejsze elementy

- launcher KOMPAS jako główne okno aplikacji;
- Dashboard epizodów jako podstawowy ekran pracy koordynatora;
- moduły Programy, Ścieżki, Pacjenci/Epizody i Administracja;
- centralne Ustawienia systemu;
- integracja z Eskulapem przez Gateway;
- harmonogram pracy oparty o widok
  `ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ`;
- synchronizacja epizodów z wizytami Eskulapa;
- centralne wyliczanie stanu epizodu przez `EpisodeStateService`;
- PostgreSQL jako jedyna baza procesowa KOMPAS;
- instalator Windows przygotowywany przez Inno Setup.

## Zasady danych

- Oracle/Eskulap pozostaje źródłem prawdy dla pacjentów i danych medycznych.
- KOMPAS nie zapisuje nic do Oracle.
- PostgreSQL przechowuje dane procesowe i konfigurację.
- Dane osobowe pacjenta nie są duplikowane w bazie KOMPAS.

## Wymagania instalacyjne

- Windows x64;
- dostęp do centralnej bazy PostgreSQL KOMPAS;
- dostęp odczytowy do widoków Oracle/Eskulap;
- poprawny `config.ini` z sekcjami Oracle i `kompas_db`.

## Build

```text
build_exe.bat
build_installer.bat
```

Oczekiwane artefakty:

```text
release/KOMPAS_1.0.0/
release/installers/KOMPAS_Setup_1.0.0.exe
```

## Testy rekomendowane przed publikacją

```text
python scripts/test_db_postgres.py
python scripts/test_business_dictionaries.py
python scripts/test_episode_synchronization.py
python scripts/test_episode_state_service.py
python scripts/test_episode_details_presenter.py
python scripts/test_schedule_data_source.py
python scripts/test_no_direct_oracle_in_schedule.py
```

Testy integracyjne Gateway i harmonogramu należy uruchomić w środowisku
z dostępem do Oracle.

## Znane ograniczenia

- część testów integracyjnych wymaga rzeczywistych połączeń do Oracle lub
  PostgreSQL;
- słowniki biznesowe są przygotowane architektonicznie, a pełna edycja
  administracyjna pozostaje elementem roadmapy po 1.0;
- mapowania konsultacji i badań pozostają obszarem dalszego rozwoju.
