# Audyt słowników i danych konfiguracyjnych KOMPAS

Data audytu: 2026-07-05

## Cel i zakres

Audyt obejmuje definicje SQLite i PostgreSQL, dane startowe, migracje,
repozytoria, usługi, modele oraz interfejs użytkownika. Nie wprowadza zmian
w działaniu aplikacji ani w strukturze baz danych.

Najważniejszy wniosek: KOMPAS ma już kilka prawidłowych słowników w bazie,
ale wartości sterujące przebiegiem procesu są rozproszone pomiędzy schematem,
seedem, repozytoriami, usługami i UI. Przed umożliwieniem administratorowi
edycji należy rozdzielić:

- słowniki biznesowe, których zawartość może się rozwijać;
- kody systemowe, od których zależą algorytmy i walidacja;
- dane referencyjne pochodzące wyłącznie z Eskulapa;
- ustawienia techniczne i bezpieczeństwa.

## Inwentaryzacja

| Nazwa słownika lub konfiguracji | Obecna lokalizacja | Główne pliki | Edycja przez administratora | Rekomendacja |
|---|---|---|---|---|
| Statusy epizodów | Kod oraz domyślna wartość w SQLite/PostgreSQL; brak tabeli słownikowej i ograniczenia `CHECK` | `db/schema.sql`, `db/postgres/003_schema.sql`, `episode_generator.py`, `app/repositories/episode_dashboard_repository.py`, UI epizodów | Docelowo kontrolowana | Przenieść do dedykowanego słownika statusów i dodać model dozwolonych przejść. W pierwszym etapie tylko podgląd; kodów systemowych nie wolno dowolnie usuwać ani zmieniać. |
| Statusy zadań | Kod, SQL i domyślna wartość w obu bazach; brak tabeli słownikowej | `db/schema.sql`, `db/postgres/003_schema.sql`, `episode_generator.py`, `app/repositories/task_repository.py`, `app/repositories/episode_repository.py`, `services/synchronization_service.py`, `app/repositories/episode_dashboard_repository.py`, `app/ui/tasks_window.py` | Docelowo kontrolowana | Najwyższy priorytet normalizacji. Utworzyć kanoniczne kody i przejścia statusów. W module administracyjnym początkowo tylko podgląd i edycja etykiety/kolejności, bez zmiany kodu. |
| Status prezentacyjny elementu bez zadania | Kod w UI: `OCZEKUJE NA AKTYWACJĘ` | `app/ui/episode_details_window.py` | Nie | Zostawić jako etykietę prezentacyjną albo przenieść do zasobów językowych. Nie jest stanem zapisanym w bazie. |
| Typy elementów procesu | Tabela `pk_typy_elementow` w SQLite i PostgreSQL, wartości w obu seedach | `db/schema.sql`, `db/seed.sql`, `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql` | Tak, z ograniczeniami | Pełna edycja nazw i aktywności; dodawanie nowych typów dozwolone. Najpierw powiązać `pk_klocki.typ` kluczem obcym lub identyfikatorem typu. |
| Biblioteka klocków procesu | Tabela `pk_klocki` w obu bazach, wartości w seedach i migracji SQLite | `db/schema.sql`, `db/seed.sql`, `db/migrations.sql`, `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql`, `app/repositories/pathway_repository.py` | Tak, z ochroną używanych rekordów | Pełna edycja nazwy, opisu, ikony i aktywności. Kod i typ powinny być chronione, gdy klocek jest używany przez ścieżkę. Preferować dezaktywację zamiast usuwania. |
| Typy wyzwalaczy | `CHECK` w obu bazach oraz duplikaty w repozytorium i UI | `db/schema.sql`, `db/postgres/003_schema.sql`, `app/repositories/trigger_repository.py`, `app/ui/triggers_window.py`, `episode_generator.py` | Tylko podgląd | Zostawić jako zamknięty słownik systemowy: `START_EPIZODU`, `PO_ZAKONCZENIU`, `PO_ZLECENIU`, `PO_WYNIKU`, `RECZNIE`. Etykiety mogą być konfigurowalne, ale dodanie kodu wymaga implementacji jego semantyki. |
| Typy zależności | `CHECK` w obu bazach oraz duplikaty w repozytorium i UI | `db/schema.sql`, `db/postgres/003_schema.sql`, `app/repositories/dependency_repository.py`, `app/ui/dependencies_window.py` | Tylko podgląd | Zostawić w kodzie jako enum systemowy: `KOLEJNOSC`, `WARUNEK`. W bazie zachować `CHECK`; w UI administracyjnym wyświetlać opis działania. |
| Role użytkowników | Tabela `pk_roles` w obu bazach, wartości w seedach i migracji; kod `ADMIN` ma specjalne znaczenie w usługach | `db/schema.sql`, `db/seed.sql`, `db/migrations.sql`, `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql`, `app/repositories/role_repository.py`, `app/services/auth_service.py` | Ograniczona | Role są już słownikiem bazodanowym. Pozwolić edytować nazwy i przypisania, ale chronić kody systemowe `ADMIN`, `KOORDYNATOR`, `KIEROWNIK`; szczególnie nie pozwalać usunąć ostatniego administratora. |
| Stany konta użytkownika | Flagi i pola: `is_active`, `locked_at`, `must_change_password`, `failed_login_count`; etykiety w UI | schematy obu baz, `app/services/auth_service.py`, `app/repositories/user_repository.py`, `app/ui/users_window.py` | Nie jako słownik | Zostawić jako model stanu konta i akcje „zablokuj/odblokuj”. `AKTYWNY`/`ZABLOKOWANY` są prezentacją pól, a nie edytowalnym słownikiem. |
| Jednostki czasu | Kod w UI oraz wartości w seedach ścieżek: `DZIEN`, `TYDZIEN`, `MIESIAC` | `app/ui/pathways_window.py`, `db/seed.sql`, `db/postgres/004_seed.sql` | Ograniczona | Przenieść do małego słownika bazodanowego z kodem, polską nazwą, kolejnością i aktywnością. Kody powinny być systemowe; administrator może zmieniać etykietę i aktywność. |
| Podstawa liczenia terminu | Kod w UI i seedzie: `START_PROGRAMU`; identyfikator innego elementu jest zapisywany jako tekst | `app/ui/pathways_window.py`, `db/seed.sql`, `db/postgres/004_seed.sql`, kolumna `termin_od` | Nie jako zwykły słownik | Rozdzielić techniczny typ podstawy terminu od identyfikatora elementu. Wymaga zmiany modelu, dlatego nie obejmować pierwszą edycją słowników. |
| Reguły aktywacji elementu | Kody generowane w UI: `PO_WYSTAWIENIU_W_ESKULAPIE`, `STATUS_EPIZODU`; równolegle istnieją wyzwalacze | `app/ui/pathways_window.py`, kolumna `warunek_aktywacji`, `pk_wyzwalacze` | Nie | Nie tworzyć drugiego edytowalnego słownika. Docelowo ujednolicić aktywację wokół `pk_wyzwalacze`; obecne wartości pokazać w audycie jako dane wymagające migracji. |
| Źródła epizodów | Kod: `ESKULAP`, `WIZYTA_KWALIFIKACYJNA_PKK`; pola tekstowe bez ograniczeń | `app/repositories/qualification_repository.py`, `episode_generator.py`, kolumny `source_system`, `source_type` | Tylko podgląd | Zostawić jako zamknięte kody integracyjne. Administrator nie powinien tworzyć dowolnych systemów źródłowych. Dodać centralne enumy i walidację. |
| Źródła zadań | Domyślna wartość `PROGRAM`; pola integracyjne `eskulap_system`, `eskulap_id` | schematy obu baz, `episode_generator.py`, repozytoria zadań i epizodów | Tylko podgląd | Ustalić kanoniczne źródła, np. `PROGRAM`, `ESKULAP`, `RECZNIE`, ale ich semantykę pozostawić w kodzie. W pierwszym etapie pokazywać tylko opis. |
| Typy zdarzeń medycznych | Stałe: `VISIT`, `CONSULTATION`, `LABORATORY_ORDER`, `IMAGING_ORDER` | `app/repositories/event_repository.py`, modele zdarzeń, `services/synchronization_service.py` | Nie | Są kontraktem Gateway i synchronizacji. Zostawić w kodzie jako enum techniczny; opcjonalnie pokazać w administracji tylko do odczytu. |
| Klasyfikacja rodzajów badań z Oracle | Zbiory kodów laboratoryjnych i obrazowych w kodzie | `app/repositories/event_repository.py`: `LABORATORY_TYPES`, `IMAGING_TYPES` | Docelowo kontrolowana | Przenieść do tabeli mapowań integracyjnych „kod Eskulapa → typ zdarzenia”. Edycję ograniczyć do administratora technicznego i walidować przed zapisem. |
| Typy konsultacji | Brak lokalnego słownika; konsultacje są pobierane jako jeden typ zdarzenia, a szczegóły pochodzą z Oracle | `app/repositories/patient_repository.py`, `app/repositories/event_repository.py`, widok `V_KOMPAS_KONSULTACJE` | Nie na obecnym etapie | Oracle pozostaje źródłem prawdy. Jeśli potrzebne będzie grupowanie, dodać mapowanie kodów Oracle, nie kopiować słownika medycznego do KOMPAS bez potrzeby. |
| Mapowanie klocków na zdarzenia Eskulapa | Słownik w kodzie `TASK_EVENT_TYPES` | `services/synchronization_service.py` | Docelowo kontrolowana | Przenieść do dedykowanej konfiguracji integracji powiązanej z `pk_klocki`. Nie oferować pełnej edycji, dopóki nie powstanie walidacja konfliktów i test dopasowania. |
| Filtr wizyty kwalifikacyjnej PKK | Słownik w kodzie: `kwalifikacja`, `PKK`, `kwalifikacyjna` | `app/repositories/qualification_repository.py`: `QUALIFICATION_FILTER` | Tak, kontrolowana | Wysoki priorytet. Przenieść do konfiguracji per jednostka lub globalnej, z ekranem testowego podglądu wyników przed zapisaniem. |
| Jednostki organizacyjne | Źródło w Oracle przez Gateway; lokalnie tylko identyfikatory i opisowe migawki przypisań użytkownika/programu/ścieżki | `app/repositories/organizational_unit_repository.py`, `app/gateway/eskulap_gateway.py`, `pk_user_units`, `pk_program_units`, `pk_pathway_units` | Tylko przypisania | Nie tworzyć lokalnego słownika jednostek. Lista zawsze pochodzi z Eskulapa; administrator zarządza jedynie przypisaniami. |
| Programy i ścieżki | Tabele w obu bazach, dane przykładowe ADHD w seedach, istniejące moduły administracyjne | `pk_programy`, `pk_sciezki`, `pk_sciezka_elementy`, seedy, repozytoria i UI programów/ścieżek | Tak, w istniejących modułach | Traktować jako konfigurację procesu, nie jako ogólny słownik. Pozostawić w modułach „Programy” i „Ścieżki”. |
| Aktywność programu, ścieżki, klocka i elementu | Flagi `czy_aktywny`/`czy_aktywna` z wartościami 0/1 | schematy obu baz oraz odpowiednie repozytoria i UI | Tak, przez akcję aktywuj/dezaktywuj | Nie tworzyć słownika `AKTYWNY/NIEAKTYWNY`. Zachować flagi i spójne polskie etykiety prezentacyjne. |
| Domyślne teksty i etykiety UI | Literały w wielu plikach UI: „brak”, „Nie przypisano”, komunikaty i nazwy statusów | `app/ui/*.py`, `app/ui/ui_helpers.py` | Nie | Docelowo przenieść do zasobów lokalizacyjnych, nie do tabel słownikowych. Administrator nie powinien edytować komunikatów systemowych. |
| Konfiguracja harmonogramu i połączeń | `config.ini`/`config.example.ini` z wartościami domyślnymi w `config.py`; konfiguracja silnika w `db_connection.py` | `config.py`, `config.example.ini`, `app/repositories/db_connection.py` | Osobny moduł ustawień | Nie mieszać ze słownikami. Parametry harmonogramu można później udostępnić w „Ustawieniach systemowych”; dane dostępowe pozostają poza UI i repozytorium. |
| Polityka bezpieczeństwa logowania | Stałe PBKDF2, długość hasła, liczba prób i blokada | `app/services/auth_service.py` | Nie w module Słowniki | Zostawić w kodzie lub bezpiecznej konfiguracji wdrożeniowej. Nie udostępniać jako zwykłej edycji administratorowi aplikacyjnemu. |

## Znalezione wartości

### Już przechowywane w bazie

- Role: `ADMIN`, `KOORDYNATOR`, `KIEROWNIK`.
- Typy elementów: `PKK`, `WIZYTA`, `SESJA`, `KONSULTACJA`, `LAB`,
  `GENETYKA`, `OBRAZOWE`, `KONSYLIUM`, `RAPORT`, `ZAMKNIECIE`.
- Biblioteka klocków, m.in. kwalifikacja, wizyty, konsultacje, badania,
  konsylium, raport i zamknięcie programu.
- Programy, ścieżki, elementy ścieżek i ich parametry.
- Wyzwalacze i zależności jako rekordy, przy czym ich dozwolone typy są
  narzucone przez kod i ograniczenia schematu.
- Przypisania użytkowników, programów i ścieżek do jednostek Eskulapa.

SQLite i PostgreSQL mają zasadniczo ten sam model słowników, ale utrzymują
oddzielne seedy. SQLite dodatkowo wykonuje `db/migrations.sql`, który również
zawiera wartości ról, klocków i wyzwalaczy.

### Zapisane na sztywno w kodzie

- Statusy epizodów i zadań oraz ich warianty pisowni.
- Typy wyzwalaczy i zależności oraz ich polskie etykiety.
- Specjalne znaczenie roli `ADMIN`.
- Jednostki czasu i część sposobów liczenia terminu.
- Kody aktywacji elementu.
- System i typ źródła epizodu kwalifikacyjnego.
- Typy zdarzeń Gateway, klasyfikacja badań oraz mapowanie klocków na zdarzenia.
- Kryteria rozpoznawania wizyty kwalifikacyjnej PKK.
- Teksty zastępcze oraz komunikaty prezentacyjne UI.
- Parametry bezpieczeństwa logowania i wartości domyślne konfiguracji.

## Stwierdzone niespójności i ryzyka

### 1. Brak jednego kanonicznego statusu zakończonego zadania

Występują co najmniej:

- `ZAKONCZONE` — generator;
- `ZREALIZOWANO` — synchronizacja, akcja UI i reguły bezpieczeństwa ścieżek;
- `ZREALIZOWANE` — część filtrów repozytoriów;
- dodatkowe warianty zgodnościowe w dashboardzie.

To nie jest wyłącznie problem nazewnictwa. `task_repository.py` nie uznaje
`ZREALIZOWANO` za status terminalny, mimo że synchronizacja właśnie taką
wartość zapisuje. Zadanie może więc pozostać na liście aktywnych.

### 2. `pk_typy_elementow` nie steruje typem klocka

Tabela słownikowa istnieje, ale `pk_klocki.typ` jest niezależnym polem
tekstowym bez klucza obcego. Administrator mógłby zmienić słownik typów bez
wpływu na bibliotekę klocków albo wpisać w klocku kod spoza słownika.

### 3. Te same enumy są powielone

Typy wyzwalaczy i zależności występują równolegle w:

- ograniczeniach SQLite;
- ograniczeniach PostgreSQL;
- walidacji repozytorium;
- etykietach i listach UI;
- generatorze epizodów.

Dodanie wartości tylko w jednym miejscu prowadzi do niespójności.

### 4. Integracja z Eskulapem zależy od niejawnych mapowań

Klasyfikacja badań, mapowanie klocków na zdarzenia oraz filtr wizyt
kwalifikacyjnych są zapisane w Pythonie. Ich zmiana wymaga wydania nowej
wersji aplikacji, chociaż są zależne od konfiguracji konkretnego Eskulapa.

### 5. Role są w bazie, ale nie wszystkie są dynamiczne

Repozytorium pobiera role z bazy, lecz kod `ADMIN` steruje autoryzacją i
ochroną ostatniego administratora. Dowolna edycja kodu roli mogłaby odebrać
dostęp administracyjny.

### 6. Nie każda widoczna wartość jest słownikiem

`AKTYWNY`, `ZABLOKOWANY`, `brak`, `Nie przypisano` i
`OCZEKUJE NA AKTYWACJĘ` są prezentacją flag, braku danych albo stanu
wyliczanego. Tworzenie dla nich tabel słownikowych nie przyniesie korzyści.

## Rekomendowany model docelowy

Nie należy umieszczać wszystkich wartości w jednej dowolnie edytowalnej
tabeli `klucz/wartość`. Statusy i integracje wymagają silniejszego kontraktu.

Rekomendowane grupy:

1. **Słowniki biznesowe** — typy elementów i biblioteka klocków; normalne
   tabele domenowe, aktywność zamiast fizycznego usuwania.
2. **Słowniki procesowe** — statusy epizodów i zadań; dedykowane tabele z
   kodem systemowym, etykietą, kolejnością, flagą terminalności i dozwolonymi
   przejściami.
3. **Enumy systemowe** — typy wyzwalaczy, zależności i źródeł; kod pozostaje
   chroniony, a moduł administracyjny oferuje głównie podgląd.
4. **Mapowania integracyjne** — kody badań Oracle, klocki odpowiadające
   zdarzeniom i filtry kwalifikacji; osobne tabele z audytem zmian oraz
   możliwością testu konfiguracji.
5. **Dane referencyjne Eskulapa** — jednostki, dane medyczne i pacjenci;
   wyłącznie odczyt przez Gateway, bez lokalnej kopii słownika.
6. **Ustawienia techniczne** — połączenia, harmonogram i bezpieczeństwo;
   poza modułem „Słowniki”.

Każda przyszła tabela edytowalna powinna mieć co najmniej:

- niezmienny kod;
- polską nazwę;
- opcjonalny opis;
- kolejność prezentacji;
- flagę aktywności;
- oznaczenie wartości systemowej;
- datę i użytkownika ostatniej zmiany;
- ochronę przed usunięciem wartości już użytej.

## Rekomendacja dla pierwszego etapu „Administracja → Słowniki”

Pierwszy etap powinien być zachowawczy:

1. Dodać ekran katalogowy pokazujący wszystkie grupy słowników i ich źródło.
2. Udostępnić kontrolowaną edycję istniejących danych bazodanowych:
   - typów elementów;
   - biblioteki klocków.
3. Dla ról umożliwić podgląd i ewentualnie zmianę nazwy, ale zablokować zmianę
   kodu oraz usuwanie ról systemowych.
4. Statusy, typy wyzwalaczy, typy zależności i źródła pokazać tylko do
   odczytu do czasu ich centralizacji.
5. Przed pełną edycją typów elementów połączyć `pk_klocki` z
   `pk_typy_elementow` relacją referencyjną.
6. Jako osobne, następne zadanie najpierw ujednolicić statusy zadań, ponieważ
   obecny rozjazd wpływa na logikę aplikacji.
7. W kolejnym etapie dodać kontrolowane mapowania integracyjne:
   filtr wizyty kwalifikacyjnej, klasyfikację badań i mapowanie klocków na
   zdarzenia Eskulapa.

Taki zakres daje administratorowi użyteczną kontrolę nad słownikami
biznesowymi, ale nie pozwala przypadkowo zmienić kodów, od których zależą
generator, synchronizacja, autoryzacja i walidacja procesu.
