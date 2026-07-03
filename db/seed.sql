INSERT OR IGNORE INTO pk_typy_elementow(kod, nazwa) VALUES
('PKK', 'Punkt konsultacyjno-koordynacyjny'),
('WIZYTA', 'Wizyta'),
('SESJA', 'Sesja terapeutyczna'),
('KONSULTACJA', 'Konsultacja specjalistyczna'),
('LAB', 'Badanie laboratoryjne'),
('GENETYKA', 'Badanie genetyczne'),
('OBRAZOWE', 'Badanie obrazowe'),
('KONSYLIUM', 'Konsylium'),
('RAPORT', 'Raport końcowy'),
('ZAMKNIECIE', 'Zamknięcie programu');

INSERT OR IGNORE INTO pk_programy(kod, nazwa, wersja, opis)
VALUES (
    'ADHD_DZ_ML',
    'Diagnostyka i leczenie ADHD u dzieci i młodzieży',
    '2.0',
    'Program diagnostyczno-terapeutyczny ADHD'
);

INSERT OR IGNORE INTO pk_sciezki(program_id, kod, nazwa, opis)
SELECT program_id, 'PODSTAWOWA', 'Ścieżka podstawowa', 'Podstawowa ścieżka diagnostyczno-terapeutyczna'
FROM pk_programy
WHERE kod = 'ADHD_DZ_ML';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 1, 'Kwalifikacja / PKK', t.typ_id, 'PKK',
       1, 1, 1, 0, NULL, NULL, NULL,
       'Początek organizacyjnej obsługi pacjenta w programie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'PKK';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 2, 'Porady psychiatryczne diagnostyczne', t.typ_id, 'PSYCHIATRA',
       1, 3, 1, 0, NULL, NULL, NULL,
       'Do 3 porad psychiatrycznych diagnostycznych w programie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'WIZYTA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 3, 'Porady psychologiczne diagnostyczne', t.typ_id, 'PSYCHOLOG',
       3, 8, 1, 0, NULL, NULL, NULL,
       'Podstawowo do 3 porad, maksymalnie do 8 porad psychologicznych diagnostycznych.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'WIZYTA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 4, 'Konsultacje specjalistyczne', t.typ_id, 'SPECJALISTYCZNA',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pojawia się po zleceniu przez lekarza w Eskulapie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'KONSULTACJA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 5, 'Badania laboratoryjne', t.typ_id, 'LAB',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pobranie materiału planowane przez koordynatora po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'LAB';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 6, 'Badania genetyczne', t.typ_id, 'GENETYKA',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pobranie materiału w PKK po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'GENETYKA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 7, 'Badania obrazowe', t.typ_id, 'OBRAZOWE',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy, np. EEG, EKG, MRI, TK. Pojawia się po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'OBRAZOWE';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 8, 'Konsylium zespołu', t.typ_id, 'KONSYLIUM',
       1, 1, 1, 0, NULL, NULL, NULL,
       'Podsumowanie diagnostyki, zebranie wyników, diagnoza, zalecenia.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'KONSYLIUM';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, lp, nazwa, typ_id, podtyp,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, 9, 'Raport końcowy / plan dalszego postępowania', t.typ_id, 'RAPORT',
       1, 1, 1, 0, 12, 'TYDZIEN', 'START_PROGRAMU',
       'Zakończenie 12-tygodniowej ścieżki: raport i decyzja o dalszym postępowaniu.'
FROM pk_sciezki s, pk_typy_elementow t
WHERE s.kod = 'PODSTAWOWA' AND t.kod = 'RAPORT';