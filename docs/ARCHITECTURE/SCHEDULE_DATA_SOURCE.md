# Źródło danych harmonogramu pracy

## Rzeczywisty przepływ danych

Moduł **Harmonogram pracy / Kalendarz** pobiera dane planu pracy z Oracle
wyłącznie przez warstwę Gateway.

```text
UI Harmonogramu
→ ScheduleService
→ EskulapGateway.get_work_schedule(...)
→ work_schedule_repository.list_work_schedule(...)
→ ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ
→ Oracle / Eskulap
```

```mermaid
flowchart LR
    UI["UI Harmonogramu<br/>plan_pracy.py"]
    S["ScheduleService"]
    G["EskulapGateway<br/>get_work_schedule"]
    R["work_schedule_repository<br/>list_work_schedule"]
    W["RI_PLAN_PRACY_WARUNKI_NEW<br/>PLW_WP_PARAMETR"]
    V[("ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ")]
    O[("Oracle / Eskulap")]
    L["Lokalny cache nazw<br/>pk_mapowanie_wizyt"]

    UI --> S
    S --> G
    G --> R
    R --> V
    W -->|"LISTAGG po PLN_ID"| V
    V --> O
    L -->|"nazwy rodzajów wizyt"| S
```

`plan_pracy.py` nie wykonuje SQL i nie otwiera połączenia Oracle. UI zna
wyłącznie `ScheduleService`.

## Widok Oracle

| Właściwość | Wartość |
|---|---|
| Właściciel widoku | `ESK_RAPORTY` |
| Nazwa widoku | `V_KOMPAS_PLAN_PRACY_KALENDARZ` |
| Pełna nazwa | `ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ` |
| Tryb użycia | tylko odczyt, wyłącznie `SELECT` |
| Konfiguracja | `application.view_name` w `config.ini` |
| Wartość domyślna | `ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ` |

`application.view_name` istnieje jako ustawienie techniczne dla środowisk,
ale zatwierdzonym źródłem harmonogramu KOMPAS jest
`ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ`. Zmiana tej wartości w konfiguracji
powinna być traktowana jako odstępstwo architektoniczne i wymaga osobnej
decyzji technicznej.

## Używane kolumny

Repozytorium `work_schedule_repository` pobiera z widoku następujące kolumny:

- `JO_ID` — identyfikator jednostki organizacyjnej,
- `JO_SYMBOL` — symbol jednostki,
- `JO_NAZWA` — nazwa jednostki,
- `DATA_DNIA` — dzień planu pracy,
- `DATA_TEKST` — data w postaci tekstowej,
- `DZIEN_TYG` — dzień tygodnia,
- `PRACOWNIK_ID` — identyfikator pracownika,
- `PRACOWNIK` — nazwa prezentacyjna pracownika,
- `GODZ_OD` — początek pracy,
- `GODZ_DO` — koniec pracy,
- `PLN_ID` — identyfikator pozycji planu,
- `PLN_OPIS` — opis pozycji planu,
- `RODZAJE_WIZYT_KODY` — zagregowana lista kodów rodzajów wizyt.

`RODZAJE_WIZYT_KODY` pochodzi z
`RI_OWNER.RI_PLAN_PRACY_WARUNKI_NEW.PLW_WP_PARAMETR`. Widok agreguje kody
po `PLN_ID` przez `LISTAGG`, dzięki czemu jeden rekord planu nadal pozostaje
jednym rekordem harmonogramu, nawet jeżeli ma wiele dopuszczonych rodzajów
wizyt.

`ScheduleService` mapuje te wartości do `DataFrame` z kolumnami używanymi
przez `calendar_logic.py`. Logika kalendarza pozostaje czysta: nie zna
Oracle, SQL ani danych połączenia.

Nazwy rodzajów wizyt do okna szczegółów komórki uzupełnia `ScheduleService`
z lokalnego cache mapowania rodzajów wizyt (`pk_mapowanie_wizyt`). Jeżeli
brakuje nazwy dla kodu, UI pokazuje kod z informacją „brak nazwy w słowniku”.

## Filtrowanie

Plan pracy jest filtrowany po:

- jednostce organizacyjnej:
  `JO_ID = :jo_id`,
- zakresie dat:
  `DATA_DNIA BETWEEN TO_DATE(:date_from, 'YYYY-MM-DD') AND TO_DATE(:date_to, 'YYYY-MM-DD')`,
- opcjonalnie po pracownikach:
  `PRACOWNIK_ID IN (...)`.

Wynik jest sortowany po:

```text
DATA_DNIA, GODZ_OD, PRACOWNIK
```

## Odpowiedzialności warstw

| Warstwa | Odpowiedzialność |
|---|---|
| `plan_pracy.py` | UI harmonogramu, wybór jednostki i dat, rysowanie tabeli |
| `ScheduleService` | walidacja zakresu dat, wywołanie Gateway, przygotowanie danych dla kalendarza |
| `EskulapGateway` | publiczna metoda `get_work_schedule(...)` |
| `work_schedule_repository` | wewnętrzny odczyt Oracle z widoku harmonogramu |
| `calendar_logic.py` | czysta transformacja dat i przedziałów godzinowych |

## Test strażniczy

Zgodność kodu z dokumentacją sprawdza:

```text
python scripts/test_schedule_data_source.py
```

Test kończy się błędem, jeżeli Harmonogram pracy omija `ScheduleService`,
omija `EskulapGateway` albo przestaje wskazywać na zatwierdzony widok
`ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ`.
