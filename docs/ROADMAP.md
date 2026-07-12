# Roadmap po wydaniu 1.0

Ten dokument opisuje kierunek rozwoju po stabilizacji KOMPAS 1.0.
Nie jest listą funkcji wymaganych do oznaczenia bieżącej wersji.

## Priorytet 1 — stabilność operacyjna

- monitoring błędów synchronizacji z Eskulapem;
- rozszerzenie logowania diagnostycznego bez ujawniania danych wrażliwych;
- testy regresji dla Dashboardu, Szczegółów epizodu i Harmonogramu;
- automatyczna walidacja skryptów PostgreSQL przed wydaniem.

## Priorytet 2 — administracja i konfiguracja

- edycja słowników biznesowych w module Ustawienia systemu;
- kontrolowana edycja mapowania rodzajów wizyt;
- konfiguracja filtrów integracji Eskulap bez zmian w kodzie;
- podgląd wersji bazy i diagnostyka połączeń.

## Priorytet 3 — proces koordynatora

- pełniejsza obsługa konsultacji i badań w synchronizacji epizodów;
- powiadomienia o zadaniach po terminie;
- raporty postępu programu;
- eksport danych procesowych bez danych osobowych pacjenta.

## Priorytet 4 — jakość UI

- dalsze ujednolicenie formularzy administracyjnych;
- uspójnienie walidacji komunikatów użytkownika;
- testy manualne w rozdzielczości 1366×768 i wyższych;
- przygotowanie dokumentacji użytkownika.

## Priorytet 5 — wydania

- checklisty release;
- podpisywanie instalatora;
- automatyczne budowanie paczek release;
- procedura rollbacku klienta i bazy.
