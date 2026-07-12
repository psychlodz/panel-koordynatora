# Changelog

Wszystkie istotne zmiany w projekcie KOMPAS są dokumentowane w tym pliku.

## [1.0.0] - 2026-07-12

### Dodano

- launcher KOMPAS jako główne okno aplikacji;
- Dashboard epizodów jako główny ekran pracy koordynatora;
- moduły Programy, Ścieżki, Pacjenci/Epizody, Wizyty kwalifikacyjne PKK
  oraz Ustawienia systemu;
- centralną bazę procesową PostgreSQL;
- integrację odczytową z Eskulapem przez `EskulapGateway`;
- centralne wyliczanie stanu epizodu przez `EpisodeStateService`;
- synchronizację epizodów z wizytami Eskulapa przez
  `EpisodeSynchronizationService`;
- słowniki biznesowe, bibliotekę klocków procesu i mapowanie rodzajów wizyt;
- centralny styl QSS i ujednolicony wygląd tabel oraz przycisków;
- skrypty budowania EXE i instalatora Windows;
- dokumentację instalacji PostgreSQL, klienta Windows, Gateway, architektury
  i release notes.

### Zmieniono

- PostgreSQL jest jedyną bazą procesową KOMPAS;
- Oracle/Eskulap jest wyłącznie źródłem odczytu danych pacjenta, medycznych
  i referencyjnych;
- UI nie odwołuje się bezpośrednio do Oracle;
- Harmonogram pracy pobiera dane przez `ScheduleService` i `EskulapGateway`;
- Dashboard i Szczegóły epizodu korzystają z tego samego centralnego stanu;
- instalator i build używają wersji `1.0.0`.

### Usunięto

- historyczne pliki lokalnego trybu SQLite;
- stary skrypt instalatora `setup_inno.iss` dla wersji 0.9;
- wygenerowany instalator binarny z repozytorium;
- stary plik `README.txt` opisujący aplikację PlanPracy;
- nieaktualny opis architektury PlanPracy.

### Bezpieczeństwo i prywatność

- KOMPAS nie kopiuje PESEL-u, imienia, nazwiska ani danych kontaktowych
  pacjenta do bazy procesowej;
- dane osobowe pacjenta są pobierane na żądanie z Oracle przez Gateway;
- `config.ini` nie jest pakowany jako plik produkcyjny z hasłami.

## [0.9] - 2026-07-02

### Dodano

- bezpieczny przykładowy plik konfiguracji `config.example.ini`;
- początkowy opis architektury;
- etapowy plan refaktoryzacji;
- plik changeloga.

### Bezpieczeństwo

- potwierdzono, że lokalny plik `config.ini` z danymi dostępowymi jest
  ignorowany przez Git.
