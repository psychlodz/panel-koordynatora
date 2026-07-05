# SQLite — archiwum historyczne

Ten katalog zawiera historyczny schemat, seed, inicjalizator i testy
lokalnego trybu SQLite. Od DB-PG-3 pliki te:

- nie są importowane przez aplikację;
- nie są dołączane do pakietu EXE;
- nie są wspieranym sposobem uruchamiania KOMPAS;
- służą wyłącznie jako materiał historyczny.

KOMPAS wymaga centralnej bazy PostgreSQL skonfigurowanej w sekcji
`[kompas_db]`. Nie uruchamiaj plików z tego katalogu w środowisku
produkcyjnym.
