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

INSERT OR IGNORE INTO pk_klocki(kod, nazwa, typ, opis) VALUES
('KWALIFIKACJA', 'Kwalifikacja', 'PKK', 'Kwalifikacja pacjenta do programu.'),
('PKK', 'Punkt konsultacyjno-koordynacyjny', 'PKK', 'Obsługa pacjenta w punkcie konsultacyjno-koordynacyjnym.'),
('WIZYTA_PSYCHIATRYCZNA', 'Wizyta psychiatryczna', 'WIZYTA', 'Wizyta diagnostyczna lub kontrolna u psychiatry.'),
('DIAGNOSTYKA_PSYCHOLOGICZNA', 'Diagnostyka psychologiczna', 'WIZYTA', 'Proces diagnostyki psychologicznej.'),
('SESJA_TERAPEUTYCZNA', 'Sesja terapeutyczna', 'SESJA', 'Pojedyncza sesja terapeutyczna.'),
('PSYCHOTERAPIA', 'Psychoterapia', 'SESJA', 'Cykl psychoterapii.'),
('KONSULTACJA_SPECJALISTYCZNA', 'Konsultacja specjalistyczna', 'KONSULTACJA', 'Konsultacja u wskazanego specjalisty.'),
('BADANIE_LAB', 'Badanie laboratoryjne', 'LAB', 'Badanie laboratoryjne zlecone w programie.'),
('BADANIE_GENETYCZNE', 'Badanie genetyczne', 'GENETYKA', 'Badanie genetyczne zlecone w programie.'),
('BADANIE_OBRAZOWE', 'Badanie obrazowe', 'OBRAZOWE', 'Badanie obrazowe zlecone w programie.'),
('KONSYLIUM', 'Konsylium', 'KONSYLIUM', 'Konsylium zespołu prowadzącego program.'),
('RAPORT_KONCOWY', 'Raport końcowy', 'RAPORT', 'Raport końcowy i plan dalszego postępowania.'),
('ZAMKNIECIE_PROGRAMU', 'Zamknięcie programu', 'ZAMKNIECIE', 'Formalne zakończenie udziału w programie.');

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
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 1, 'Kwalifikacja / PKK',
       1, 1, 1, 0, NULL, NULL, NULL,
       'Początek organizacyjnej obsługi pacjenta w programie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'KWALIFIKACJA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 2, 'Porady psychiatryczne diagnostyczne',
       1, 3, 1, 0, NULL, NULL, NULL,
       'Do 3 porad psychiatrycznych diagnostycznych w programie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'WIZYTA_PSYCHIATRYCZNA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 3, 'Porady psychologiczne diagnostyczne',
       3, 8, 1, 0, NULL, NULL, NULL,
       'Podstawowo do 3 porad, maksymalnie do 8 porad psychologicznych diagnostycznych.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'DIAGNOSTYKA_PSYCHOLOGICZNA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 4, 'Konsultacje specjalistyczne',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pojawia się po zleceniu przez lekarza w Eskulapie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'KONSULTACJA_SPECJALISTYCZNA';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 5, 'Badania laboratoryjne',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pobranie materiału planowane przez koordynatora po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'BADANIE_LAB';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 6, 'Badania genetyczne',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy. Pobranie materiału w PKK po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'BADANIE_GENETYCZNE';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 7, 'Badania obrazowe',
       0, NULL, 0, 1, NULL, NULL, NULL,
       'Element warunkowy, np. EEG, EKG, MRI, TK. Pojawia się po zleceniu w Eskulapie.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'BADANIE_OBRAZOWE';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 8, 'Konsylium zespołu',
       1, 1, 1, 0, NULL, NULL, NULL,
       'Podsumowanie diagnostyki, zebranie wyników, diagnoza, zalecenia.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'KONSYLIUM';

INSERT OR IGNORE INTO pk_sciezka_elementy(
    sciezka_id, klocek_id, lp, nazwa_w_sciezce,
    min_liczba, max_liczba, czy_obowiazkowy,
    czy_wymaga_zlecenia, termin_liczba, termin_jednostka,
    termin_od, opis_organizacyjny
)
SELECT s.sciezka_id, k.klocek_id, 9, 'Raport końcowy / plan dalszego postępowania',
       1, 1, 1, 0, 12, 'TYDZIEN', 'START_PROGRAMU',
       'Zakończenie 12-tygodniowej ścieżki: raport i decyzja o dalszym postępowaniu.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'RAPORT_KONCOWY';