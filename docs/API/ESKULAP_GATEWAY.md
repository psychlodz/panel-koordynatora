# Eskulap Gateway

`EskulapGateway` jest publiczną warstwą odczytu danych medycznych
z Eskulapa. Ukrywa przed kodem wywołującym repozytoria, SQL oraz nazwy
widoków Oracle.

Gateway nie otwiera połączeń i nie wykonuje SQL. Deleguje operacje do
istniejących repozytoriów, które korzystają z fabryki połączeń w `db.py`.
Warstwa nie zapisuje żadnych danych do Oracle.

Gateway zawsze pobiera aktualne dane pacjenta z Oracle.
KOMPAS nie utrzymuje własnej kopii danych osobowych. Model `Patient` jest
wyłącznie DTO przekazywanym w pamięci i nie jest zapisywany w PostgreSQL
ani SQLite.

## Zależności

```mermaid
flowchart LR
    C["Kod aplikacji"] --> G["EskulapGateway"]
    G --> P["patient_repository"]
    G --> Q["qualification_repository"]
    G --> E["event_repository"]
    P --> D["db.py"]
    Q --> D
    E --> P
    D --> O[("Oracle / Eskulap")]
    G --> M["Modele dataclass"]
```

## Metody

### `search_patients(search_text)`

Wyszukuje pacjentów po fragmencie nazwiska lub numeru PESEL. Zwraca
listę `Patient`.

### `get_patient(patient_id)`

Pobiera jednego pacjenta. Zwraca `Patient` albo `None`.

### `get_patient_visits(patient_id)`

Pobiera wizyty pacjenta. Zwraca listę `Visit`. Model zawiera także pola
`parametr_kod`, `parametr_nazwa` i `parametr_czy_aktualne`, mapowane
odpowiednio z `WP_PARAMETR` i słownika `CG_REF_CODES`.

### `get_patient_qualification_visits(date_from=None, date_to=None, only_unassigned=True)`

Pobiera wizyty kwalifikacyjne PKK z opcjonalnego okresu. Parametr
`only_unassigned` ogranicza wynik do wizyt bez epizodu KOMPAS. Zwraca
listę `QualificationVisit`. Wizyta kwalifikacyjna jest rozpoznawana po
dokładnej wartości `PARAMETR_KOD = 'F18'`.

### `get_patient_consultations(patient_id)`

Pobiera konsultacje pacjenta. Zwraca listę `Consultation`.

### `get_patient_laboratory_orders(patient_id)`

Pobiera zlecenia badań laboratoryjnych. Zwraca listę
`LaboratoryOrder`.

### `get_patient_imaging_orders(patient_id)`

Pobiera zlecenia badań obrazowych. Zwraca listę `ImagingOrder`.

### `list_organizational_units(search_text=None)`

Pobiera jednostki organizacyjne ze źródła harmonogramu wskazanego przez
`application.view_name` w `config.ini`. Opcjonalnie filtruje po
identyfikatorze, symbolu lub nazwie. Zwraca listę `OrganizationalUnit`
z polami `jo_id`, `jo_symbol` i `jo_nazwa`. Operacja korzysta wyłącznie
z instrukcji `SELECT`.

## Użycie

```python
from app.gateway.eskulap_gateway import EskulapGateway

gateway = EskulapGateway()
patients = gateway.search_patients("Kowalski")

if patients:
    patient = gateway.get_patient(patients[0].patient_id)
    visits = gateway.get_patient_visits(patient.patient_id)
```

Gateway zwraca dataclassy, a nie `DataFrame` ani surowe wiersze Oracle.
Pola modeli mają stabilne angielskie nazwy, niezależne od nazw kolumn
źródłowych, np. `patient_id`, `first_name`, `visit_date`.

## Wymagane widoki Oracle

Gateway wymaga widoków:

- `ESK_RAPORTY.V_KOMPAS_PACJENCI`,
- `ESK_RAPORTY.V_KOMPAS_WIZYTY`,
- `ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT`,
- `ESK_RAPORTY.V_KOMPAS_KONSULTACJE`,
- `ESK_RAPORTY.V_KOMPAS_BADANIA`.

Badania laboratoryjne i obrazowe korzystają ze wspólnego widoku
`V_KOMPAS_BADANIA` i są rozdzielane według typu badania.

`RI_WIZYTY_W_PORADNIACH.WP_PARAMETR` przechowuje kod rodzaju wizyty.
Słownik `CG_REF_CODES` dla `RV_DOMAIN = 'PARAMETRY'` opisuje te kody:
`RV_LOW_VALUE` odpowiada wartości `WP_PARAMETR`, `RV_MEANING` jest nazwą
wizyty, porady, sesji lub terapii, a `RV_CZY_AKTUALNE` określa aktualność
kodu. Widok `V_KOMPAS_PARAMETRY_WIZYT` udostępnia ten słownik wyłącznie
do odczytu.

Wizyty kwalifikacyjne nie mają osobnego widoku. Gateway pobiera je
z `V_KOMPAS_WIZYTY`, filtrując `PARAMETR_KOD` po wartości `F18`.
`F18` jest kodem rodzaju wizyty kwalifikacyjnej PKK. Jedyna definicja
tego filtra znajduje się jako `PKK_KWAL_PARAMETR_KOD`
w `qualification_repository.py`.

W modelu procesu `PKK` pozostaje typem elementu. Klocek `PKK_KWAL`
reprezentuje wizytę kwalifikacyjną F18, a `PKK_WIZ` zwykłą wizytę lub
czynność organizacyjną PKK w trakcie programu.
Docelowo klocki typu wizyta, sesja i terapia będą mapowane do
`parametr_kod` wybieranego z `V_KOMPAS_PARAMETRY_WIZYT`. Pełne mapowanie
i jego interfejs administracyjny nie są jeszcze implementowane.
Techniczna wartość `source_type = WIZYTA_KWALIFIKACYJNA_PKK` opisuje
pochodzenie epizodu i nie jest kodem klocka.

Po każdej zmianie pliku `docs/SQL/kompas_oracle_views.sql` administrator
musi ręcznie wykonać odpowiednie instrukcje `CREATE OR REPLACE VIEW`
w Oracle. Aktualizacja pliku w projekcie nie modyfikuje bazy Oracle.

## Test ręczny

```text
python scripts/test_gateway.py Kowalski
python scripts/test_gateway.py 90010112345 --date-from 2026-01-01
```

Test wymaga poprawnego `config.ini`, dostępu do Oracle oraz wdrożonych
widoków `ESK_RAPORTY.V_KOMPAS_*`.
