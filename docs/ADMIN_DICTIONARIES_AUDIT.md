# Audyt słowników i konfiguracji KOMPAS 1.0

Dokument opisuje aktualny stan słowników i danych konfiguracyjnych po
stabilizacji release 1.0.

## Podsumowanie

- Dane procesowe i słowniki KOMPAS są utrzymywane w PostgreSQL.
- Dane referencyjne Eskulapa są pobierane przez Gateway i wyświetlane lub
  synchronizowane wyłącznie tam, gdzie jest to potrzebne do mapowań.
- Administrator nie powinien zmieniać kodów systemowych, od których zależy
  logika aplikacji.
- Rekordy używane w programach, ścieżkach lub epizodach powinny być
  dezaktywowane, a nie usuwane.

## Tabela audytu

| Słownik / konfiguracja | Obecna lokalizacja | Główne pliki | Edycja przez administratora | Rekomendacja |
|---|---|---|---|---|
| Typy elementów procesu | PostgreSQL, seed | `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql` | Ograniczona | Edytować nazwę, opis, ikonę, kolor i aktywność; kod systemowy chroniony. |
| Biblioteka klocków | PostgreSQL, seed | `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql`, `app/repositories/pathway_repository.py` | Tak, z ochroną użycia | Pozwalać na edycję prezentacji i aktywności; nie usuwać klocków użytych w ścieżkach. |
| Jednostki czasu | PostgreSQL, seed | `db/postgres/003_schema.sql`, `db/postgres/004_seed.sql` | Ograniczona | Udostępnić podgląd i kontrolowaną edycję etykiet; semantyka obliczeń systemowa. |
| Rodzaje wizyt Eskulapa | PostgreSQL jako słownik referencyjny synchronizowany z Oracle | `pk_rodzaje_wizyt_eskulap`, `visit_type_dictionary_sync_service.py` | Tylko podgląd | Źródłem jest Eskulap; administrator nie edytuje nazw Oracle. |
| Mapowanie rodzajów wizyt | PostgreSQL | `pk_mapowanie_wizyt`, `visit_mapping_repository.py`, `visit_mappings_widget.py` | Tak | Administrator przypisuje kody `WP_PARAMETR` do klocków procesu. |
| Role systemowe | PostgreSQL, seed | `pk_roles`, `role_repository.py`, `auth_service.py` | Ograniczona | Chronić kody `ADMIN`, `KOORDYNATOR`, `KIEROWNIK`; edytować nazwy i przypisania. |
| Statusy epizodu | Kod i dane procesowe | `EpisodeStateService`, `episode_dashboard_repository.py` | Nie w 1.0 | Pozostawić jako słownik systemowy. Ewentualna edycja etykiet po osobnym ADR. |
| Statusy zadań | Kod i dane procesowe | `EpisodeStateService`, `task_repository.py` | Nie w 1.0 | Źródłem prawdy jest wyliczenie `EpisodeStateService`; nie edytować kodów. |
| Typy zależności | Kod i ograniczenia bazy | `dependency_repository.py`, `pk_sciezka_zaleznosci` | Tylko podgląd | `KOLEJNOSC`, `WARUNEK` są systemowe. |
| Typy wyzwalaczy | Kod i ograniczenia bazy | `trigger_repository.py`, `pk_wyzwalacze` | Tylko podgląd | Kody wyzwalaczy mają semantykę w generatorze i usługach. |
| Źródła danych | Kod systemowy | `episode_synchronization_service.py`, `qualification_repository.py` | Tylko podgląd | `ESKULAP`, `PROGRAM` i typy źródłowe traktować jako techniczne. |

## Rekomendacja dla modułu „Ustawienia systemu → Słowniki”

Pierwszy etap po 1.0:

1. Podgląd typów elementów procesu.
2. Podgląd i edycja prezentacyjna biblioteki klocków.
3. Podgląd jednostek czasu.
4. Podgląd rodzajów wizyt Eskulapa.
5. Edycja mapowania rodzajów wizyt na klocki.

Zakres poza pierwszym etapem:

- edytowalne statusy biznesowe;
- model przejść statusów;
- historia zmian słowników;
- rozbudowane uprawnienia do edycji słowników.
