# Plan refaktoryzacji

Refaktoryzacja powinna przebiegać małymi krokami, z zachowaniem dotychczasowego działania programu.

## Etap 0 — porządek w repozytorium

- usunąć zbędne pliki tymczasowe;
- dodać bezpieczny przykład konfiguracji;
- udokumentować architekturę, historię zmian i plan prac;
- nie zmieniać kodu aplikacji ani SQL.

## Etap 1 — testy zachowania

- dodać testy funkcji czasu, świąt i przedziałów;
- przetestować przygotowanie danych oraz filtrowanie;
- utrwalić obecne zachowanie przed rozdzielaniem modułów.

## Etap 2 — konfiguracja

- wydzielić odczyt i walidację konfiguracji;
- dodać czytelne komunikaty o brakujących ustawieniach;
- oddzielić dane dostępowe od plików dystrybucyjnych.

## Etap 3 — dostęp do Oracle

- wydzielić repozytorium odpowiedzialne za połączenia i zapytania;
- zachować obecne zapytania i format zwracanych danych;
- dodać testowalną granicę pomiędzy bazą a aplikacją.

## Etap 4 — logika harmonogramu

- przenieść transformacje danych, sloty godzinowe i święta do osobnego modułu;
- uniezależnić logikę biznesową od PySide6;
- zoptymalizować grupowanie danych dla komórek kalendarza.

## Etap 5 — interfejs użytkownika

- pozostawić w głównym oknie jedynie obsługę kontrolek i zdarzeń;
- wykonywać operacje Oracle poza głównym wątkiem;
- dodać stan ładowania i kontrolowaną obsługę błędów.

## Etap 6 — eksport

- wydzielić generowanie Excela do osobnego serwisu;
- testować dane eksportu bez uruchamiania interfejsu.

## Etap 7 — powtarzalne wydania

- przypiąć wersje zależności;
- ograniczyć zawartość paczki PyInstallera;
- ujednolicić numer wersji;
- zautomatyzować testy, budowanie EXE i instalatora Inno Setup.
