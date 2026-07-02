# Obecna architektura

PlanPracy jest desktopową aplikacją Windows napisaną w Pythonie z użyciem PySide6.

## Główne elementy

- `plan_pracy.py` zawiera punkt startowy programu, interfejs użytkownika, obsługę konfiguracji, komunikację z Oracle, przetwarzanie danych oraz eksport do Excela.
- `PlanPracyApp` jest głównym oknem i koordynuje większość działania aplikacji.
- `PersonColorDelegate` odpowiada za kolorowe wyświetlanie pracowników w tabeli.
- `config.ini` przechowuje lokalne ustawienia aplikacji i dane połączenia z Oracle.
- `config.example.ini` pokazuje wymagany format konfiguracji bez prawdziwych danych dostępowych.

## Przepływ danych

1. Aplikacja odczytuje `config.ini`.
2. Użytkownik wybiera jednostkę i zakres dat.
3. Program otwiera połączenie przez `oracledb` i pobiera dane z widoku Oracle.
4. Dane są przetwarzane przez pandas.
5. PySide6 prezentuje plan w tabeli z filtrami pracowników.
6. Aktualny widok może zostać wyeksportowany do pliku XLSX.

## Budowanie i dystrybucja

- PyInstaller buduje aplikację katalogową `dist/PlanPracy/PlanPracy.exe` na podstawie `plan_pracy.spec`.
- `build_exe.bat` i `build_exe.ps1` automatyzują budowanie EXE.
- `setup_inno.iss` definiuje opcjonalny instalator Windows tworzony przez Inno Setup.

## Aktualne ograniczenia

Większość odpowiedzialności jest skupiona w klasie `PlanPracyApp`. Warstwy interfejsu, dostępu do danych i logiki harmonogramu nie są obecnie rozdzielone. Operacje Oracle są wykonywane synchronicznie w wątku interfejsu.
