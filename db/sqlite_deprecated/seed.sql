INSERT OR IGNORE INTO pk_roles(code, name) VALUES
('ADMIN', 'Administrator'),
('KOORDYNATOR', 'Koordynator'),
('KIEROWNIK', 'Kierownik');

INSERT OR IGNORE INTO pk_users(
    login,
    full_name,
    password_hash,
    must_change_password,
    is_active
)
VALUES (
    'admin',
    'Administrator KOMPAS',
    'pbkdf2_sha256$310000$jxejHRzgRdW5i0h/7ZfGhg==$eLtybSEQwruYGAflhclSFIyeIkjKenHsgXsFIV/BqaU=',
    1,
    1
);

INSERT OR IGNORE INTO pk_user_roles(user_id, role_id)
SELECT u.user_id, r.role_id
FROM pk_users u, pk_roles r
WHERE u.login = 'admin'
  AND r.code = 'ADMIN';

INSERT OR IGNORE INTO pk_typy_elementow(
    kod, nazwa, opis, kolejnosc, czy_aktywny, czy_systemowy
) VALUES
('PKK', 'Punkt konsultacyjno-koordynacyjny', NULL, 10, 1, 1),
('WIZYTA', 'Wizyta', NULL, 20, 1, 1),
('SESJA', 'Sesja', NULL, 30, 1, 1),
('KONSULTACJA', 'Konsultacja', NULL, 40, 1, 1),
('BADANIE_LAB', 'Badanie laboratoryjne', NULL, 50, 1, 1),
('BADANIE_GEN', 'Badanie genetyczne', NULL, 60, 1, 1),
('BADANIE_OBRAZOWE', 'Badanie obrazowe', NULL, 70, 1, 1),
('KONSYLIUM', 'Konsylium', NULL, 80, 1, 1),
('DOKUMENT', 'Dokument', NULL, 90, 1, 1),
('RAPORT', 'Raport', NULL, 100, 1, 1),
('ZAKONCZENIE', 'Zakończenie programu', NULL, 110, 1, 1);

INSERT OR IGNORE INTO pk_grupy_klockow(
    kod, nazwa, opis, kolejnosc, czy_aktywny, czy_systemowy, kolor
) VALUES
('KWALIFIKACJA', 'Kwalifikacja', NULL, 10, 1, 1, '#2E6F9E'),
('WIZYTY', 'Wizyty', NULL, 20, 1, 1, '#3A7CA5'),
('KONSULTACJE', 'Konsultacje', NULL, 30, 1, 1, '#507DBC'),
('BADANIA_LAB', 'Badania laboratoryjne', NULL, 40, 1, 1, '#2A9D8F'),
('BADANIA_OBRAZOWE', 'Badania obrazowe', NULL, 50, 1, 1, '#577590'),
('DIAGNOSTYKA', 'Diagnostyka', NULL, 60, 1, 1, '#6D597A'),
('PSYCHOTERAPIA', 'Psychoterapia', NULL, 70, 1, 1, '#8F5D78'),
('DOKUMENTACJA', 'Dokumentacja', NULL, 80, 1, 1, '#7A6C5D'),
('RAPORTY', 'Raporty', NULL, 90, 1, 1, '#5C677D'),
('ZAKONCZENIE_PROGRAMU', 'Zakończenie programu', NULL, 100, 1, 1, '#4F5D75');

INSERT OR IGNORE INTO pk_jednostki_czasu(
    kod, nazwa, opis, rodzaj_obliczenia, mnoznik,
    kolejnosc, czy_aktywny, czy_systemowy
) VALUES
('DZIEN', 'dzień', NULL, 'DNI', 1, 10, 1, 1),
('TYDZIEN', 'tydzień', NULL, 'DNI', 7, 20, 1, 1),
('MIESIAC', 'miesiąc', NULL, 'MIESIACE', 1, 30, 1, 1);

INSERT OR IGNORE INTO pk_klocki(
    kod, nazwa, opis, typ_elementu_id, grupa_id, ikona, kolor,
    domyslny_termin_liczba, domyslna_jednostka_czasu_id,
    czy_wymaga_zlecenia, czy_obowiazkowy, czy_aktywny,
    czy_systemowy, kolejnosc
)
SELECT
    dane.kod, dane.nazwa, dane.opis, typ.typ_id, grupa.grupa_id,
    dane.ikona, grupa.kolor, NULL, NULL, dane.wymaga_zlecenia,
    dane.obowiazkowy, 1, 1, dane.kolejnosc
FROM (
    SELECT 'PKK_KWAL' AS kod, 'Wizyta kwalifikacyjna w PKK' AS nazwa,
           'Wizyta kwalifikacyjna w PKK; w Eskulapie rodzaj wizyty F18.' AS opis,
           'PKK' AS typ_kod, 'KWALIFIKACJA' AS grupa_kod,
           'PKK' AS ikona, 0 AS wymaga_zlecenia, 1 AS obowiazkowy,
           10 AS kolejnosc
    UNION ALL SELECT 'PKK_WIZ', 'Wizyta w PKK',
           'Wizyta lub czynność organizacyjna realizowana w PKK w trakcie programu.',
           'PKK', 'WIZYTY', 'PKK', 0, 0, 20
    UNION ALL SELECT 'WIZYTA_PSYCHIATRYCZNA', 'Wizyta psychiatryczna',
           'Wizyta diagnostyczna lub kontrolna u psychiatry.',
           'WIZYTA', 'WIZYTY', 'WIZ', 0, 1, 30
    UNION ALL SELECT 'DIAGNOSTYKA_PSYCHOLOGICZNA', 'Diagnostyka psychologiczna',
           'Proces diagnostyki psychologicznej.',
           'WIZYTA', 'DIAGNOSTYKA', 'PSY', 0, 1, 40
    UNION ALL SELECT 'SESJA_TERAPEUTYCZNA', 'Sesja terapeutyczna',
           'Pojedyncza sesja terapeutyczna.',
           'SESJA', 'PSYCHOTERAPIA', 'SES', 0, 0, 50
    UNION ALL SELECT 'PSYCHOTERAPIA', 'Psychoterapia',
           'Cykl psychoterapii.',
           'SESJA', 'PSYCHOTERAPIA', 'PSY', 0, 0, 60
    UNION ALL SELECT 'KONSULTACJA_SPECJALISTYCZNA', 'Konsultacja specjalistyczna',
           'Konsultacja u wskazanego specjalisty.',
           'KONSULTACJA', 'KONSULTACJE', 'KON', 1, 0, 70
    UNION ALL SELECT 'BADANIE_LAB', 'Badanie laboratoryjne',
           'Badanie laboratoryjne zlecone w programie.',
           'BADANIE_LAB', 'BADANIA_LAB', 'LAB', 1, 0, 80
    UNION ALL SELECT 'BADANIE_GENETYCZNE', 'Badanie genetyczne',
           'Badanie genetyczne zlecone w programie.',
           'BADANIE_GEN', 'DIAGNOSTYKA', 'GEN', 1, 0, 90
    UNION ALL SELECT 'BADANIE_OBRAZOWE', 'Badanie obrazowe',
           'Badanie obrazowe zlecone w programie.',
           'BADANIE_OBRAZOWE', 'BADANIA_OBRAZOWE', 'OBR', 1, 0, 100
    UNION ALL SELECT 'KONSYLIUM', 'Konsylium',
           'Konsylium zespołu prowadzącego program.',
           'KONSYLIUM', 'DIAGNOSTYKA', 'KON', 0, 1, 110
    UNION ALL SELECT 'RAPORT_KONCOWY', 'Raport końcowy',
           'Raport końcowy i plan dalszego postępowania.',
           'RAPORT', 'RAPORTY', 'RAP', 0, 1, 120
    UNION ALL SELECT 'ZAMKNIECIE_PROGRAMU', 'Zamknięcie programu',
           'Formalne zakończenie udziału w programie.',
           'ZAKONCZENIE', 'ZAKONCZENIE_PROGRAMU', 'KON', 0, 1, 130
) dane
JOIN pk_typy_elementow typ ON typ.kod = dane.typ_kod
JOIN pk_grupy_klockow grupa ON grupa.kod = dane.grupa_kod;

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
SELECT s.sciezka_id, k.klocek_id, 1, 'Wizyta kwalifikacyjna w PKK',
       1, 1, 1, 0, NULL, NULL, NULL,
       'Wizyta F18 w Eskulapie będąca podstawą utworzenia epizodu.'
FROM pk_sciezki s, pk_klocki k
WHERE s.kod = 'PODSTAWOWA' AND k.kod = 'PKK_KWAL';

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
