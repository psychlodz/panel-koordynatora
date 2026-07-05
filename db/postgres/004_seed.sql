\set ON_ERROR_STOP on
SET client_encoding = 'UTF8';

BEGIN;

INSERT INTO pk_roles(code, name) VALUES
    ('ADMIN', 'Administrator'),
    ('KOORDYNATOR', 'Koordynator'),
    ('KIEROWNIK', 'Kierownik')
ON CONFLICT DO NOTHING;

-- Hash istniejącego hasła startowego środowiska developerskiego.
-- W środowisku produkcyjnym należy je zmienić natychmiast po instalacji.
INSERT INTO pk_users(
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
)
ON CONFLICT DO NOTHING;

INSERT INTO pk_user_roles(user_id, role_id)
SELECT u.user_id, r.role_id
FROM pk_users u
CROSS JOIN pk_roles r
WHERE lower(u.login) = 'admin'
  AND r.code = 'ADMIN'
ON CONFLICT DO NOTHING;

INSERT INTO pk_typy_elementow(
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
    ('ZAKONCZENIE', 'Zakończenie programu', NULL, 110, 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO pk_grupy_klockow(
    kod, nazwa, opis, kolejnosc, czy_aktywny, czy_systemowy, kolor
) VALUES
    ('KWALIFIKACJA', 'Kwalifikacja', NULL, 10, 1, 1, '#173F5F'),
    ('WIZYTY', 'Wizyty', NULL, 20, 1, 1, '#2F80ED'),
    ('KONSULTACJE', 'Konsultacje', NULL, 30, 1, 1, '#7B2CBF'),
    ('BADANIA_LAB', 'Badania laboratoryjne', NULL, 40, 1, 1, '#F2994A'),
    ('BADANIA_OBRAZOWE', 'Badania obrazowe', NULL, 50, 1, 1, '#1BA39C'),
    ('DIAGNOSTYKA', 'Diagnostyka', NULL, 60, 1, 1, '#F2C94C'),
    ('PSYCHOTERAPIA', 'Psychoterapia', NULL, 70, 1, 1, '#27AE60'),
    ('DOKUMENTACJA', 'Dokumentacja', NULL, 80, 1, 1, '#828282'),
    ('RAPORTY', 'Raporty', NULL, 90, 1, 1, '#1B365D'),
    ('ZAKONCZENIE_PROGRAMU', 'Zakończenie programu', NULL, 100, 1, 1, '#1F6B45')
ON CONFLICT DO NOTHING;

INSERT INTO pk_jednostki_czasu(
    kod, nazwa, opis, rodzaj_obliczenia, mnoznik,
    kolejnosc, czy_aktywny, czy_systemowy
) VALUES
    ('DZIEN', 'dzień', NULL, 'DNI', 1, 10, 1, 1),
    ('TYDZIEN', 'tydzień', NULL, 'DNI', 7, 20, 1, 1),
    ('MIESIAC', 'miesiąc', NULL, 'MIESIACE', 1, 30, 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO pk_klocki(
    kod, nazwa, opis, typ_elementu_id, grupa_id, ikona, kolor,
    kolor_tekstu,
    domyslny_termin_liczba, domyslna_jednostka_czasu_id,
    czy_wymaga_zlecenia, czy_obowiazkowy, czy_aktywny,
    czy_systemowy, kolejnosc
)
SELECT
    dane.kod, dane.nazwa, dane.opis, typ.typ_id, grupa.grupa_id,
    dane.ikona, grupa.kolor,
    CASE
        WHEN dane.grupa_kod IN ('BADANIA_LAB', 'DIAGNOSTYKA')
            THEN '#1F2937'
        ELSE '#FFFFFF'
    END,
    NULL, NULL, dane.wymaga_zlecenia,
    dane.obowiazkowy, 1, 1, dane.kolejnosc
FROM (
    VALUES
        (
            'PKK_KWAL', 'Wizyta kwalifikacyjna w PKK',
            'Wizyta kwalifikacyjna w PKK; w Eskulapie rodzaj wizyty F18.',
            'PKK', 'KWALIFIKACJA', 'PKK', 0, 1, 10
        ),
        (
            'PKK_WIZ', 'Wizyta w PKK',
            'Wizyta lub czynność organizacyjna realizowana w PKK w trakcie programu.',
            'PKK', 'WIZYTY', 'PKK', 0, 0, 20
        ),
        (
            'WIZYTA_PSYCHIATRYCZNA', 'Wizyta psychiatryczna',
            'Wizyta diagnostyczna lub kontrolna u psychiatry.',
            'WIZYTA', 'WIZYTY', 'WIZ', 0, 1, 30
        ),
        (
            'DIAGNOSTYKA_PSYCHOLOGICZNA', 'Diagnostyka psychologiczna',
            'Proces diagnostyki psychologicznej.',
            'WIZYTA', 'DIAGNOSTYKA', 'PSY', 0, 1, 40
        ),
        (
            'SESJA_TERAPEUTYCZNA', 'Sesja terapeutyczna',
            'Pojedyncza sesja terapeutyczna.',
            'SESJA', 'PSYCHOTERAPIA', 'SES', 0, 0, 50
        ),
        (
            'PSYCHOTERAPIA', 'Psychoterapia', 'Cykl psychoterapii.',
            'SESJA', 'PSYCHOTERAPIA', 'PSY', 0, 0, 60
        ),
        (
            'KONSULTACJA_SPECJALISTYCZNA', 'Konsultacja specjalistyczna',
            'Konsultacja u wskazanego specjalisty.',
            'KONSULTACJA', 'KONSULTACJE', 'KON', 1, 0, 70
        ),
        (
            'BADANIE_LAB', 'Badanie laboratoryjne',
            'Badanie laboratoryjne zlecone w programie.',
            'BADANIE_LAB', 'BADANIA_LAB', 'LAB', 1, 0, 80
        ),
        (
            'BADANIE_GENETYCZNE', 'Badanie genetyczne',
            'Badanie genetyczne zlecone w programie.',
            'BADANIE_GEN', 'DIAGNOSTYKA', 'GEN', 1, 0, 90
        ),
        (
            'BADANIE_OBRAZOWE', 'Badanie obrazowe',
            'Badanie obrazowe zlecone w programie.',
            'BADANIE_OBRAZOWE', 'BADANIA_OBRAZOWE', 'OBR', 1, 0, 100
        ),
        (
            'KONSYLIUM', 'Konsylium',
            'Konsylium zespołu prowadzącego program.',
            'KONSYLIUM', 'DIAGNOSTYKA', 'KON', 0, 1, 110
        ),
        (
            'RAPORT_KONCOWY', 'Raport końcowy',
            'Raport końcowy i plan dalszego postępowania.',
            'RAPORT', 'RAPORTY', 'RAP', 0, 1, 120
        ),
        (
            'ZAMKNIECIE_PROGRAMU', 'Zamknięcie programu',
            'Formalne zakończenie udziału w programie.',
            'ZAKONCZENIE', 'ZAKONCZENIE_PROGRAMU', 'KON', 0, 1, 130
        )
) AS dane(
    kod, nazwa, opis, typ_kod, grupa_kod, ikona,
    wymaga_zlecenia, obowiazkowy, kolejnosc
)
JOIN pk_typy_elementow typ ON typ.kod = dane.typ_kod
JOIN pk_grupy_klockow grupa ON grupa.kod = dane.grupa_kod
ON CONFLICT DO NOTHING;

INSERT INTO pk_mapowanie_wizyt(
    klocek_id,
    parametr_kod,
    parametr_nazwa_cache,
    czy_aktywny
)
SELECT
    k.klocek_id,
    'F18',
    'Wizyta kwalifikacyjna PKK',
    1
FROM pk_klocki k
WHERE k.kod = 'PKK_KWAL'
ON CONFLICT (parametr_kod) DO UPDATE
SET klocek_id = EXCLUDED.klocek_id,
    parametr_nazwa_cache = EXCLUDED.parametr_nazwa_cache,
    czy_aktywny = EXCLUDED.czy_aktywny,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO pk_programy(kod, nazwa, wersja, opis)
VALUES (
    'ADHD_DZ_ML',
    'Diagnostyka i leczenie ADHD u dzieci i młodzieży',
    '2.0',
    'Program diagnostyczno-terapeutyczny ADHD'
)
ON CONFLICT DO NOTHING;

INSERT INTO pk_sciezki(program_id, kod, nazwa, opis)
SELECT
    program_id,
    'PODSTAWOWA',
    'Ścieżka podstawowa',
    'Podstawowa ścieżka diagnostyczno-terapeutyczna'
FROM pk_programy
WHERE kod = 'ADHD_DZ_ML'
ON CONFLICT DO NOTHING;

INSERT INTO pk_sciezka_elementy(
    sciezka_id,
    klocek_id,
    lp,
    nazwa_w_sciezce,
    min_liczba,
    max_liczba,
    czy_obowiazkowy,
    czy_wymaga_zlecenia,
    termin_liczba,
    termin_jednostka,
    termin_od,
    opis_organizacyjny
)
SELECT
    s.sciezka_id,
    k.klocek_id,
    dane.lp,
    dane.nazwa,
    dane.min_liczba,
    dane.max_liczba,
    dane.obowiazkowy,
    dane.wymaga_zlecenia,
    dane.termin_liczba,
    dane.termin_jednostka,
    dane.termin_od,
    dane.opis
FROM pk_sciezki s
JOIN pk_programy p ON p.program_id = s.program_id
CROSS JOIN (
    VALUES
        (
            'PKK_KWAL', 1, 'Wizyta kwalifikacyjna w PKK',
            1, 1, 1, 0, NULL::integer, NULL::text, NULL::text,
            'Wizyta F18 w Eskulapie będąca podstawą utworzenia epizodu.'
        ),
        (
            'WIZYTA_PSYCHIATRYCZNA', 2,
            'Porady psychiatryczne diagnostyczne',
            1, 3, 1, 0, NULL, NULL, NULL,
            'Do 3 porad psychiatrycznych diagnostycznych w programie.'
        ),
        (
            'DIAGNOSTYKA_PSYCHOLOGICZNA', 3,
            'Porady psychologiczne diagnostyczne',
            3, 8, 1, 0, NULL, NULL, NULL,
            'Podstawowo do 3 porad, maksymalnie do 8 porad diagnostycznych.'
        ),
        (
            'KONSULTACJA_SPECJALISTYCZNA', 4,
            'Konsultacje specjalistyczne',
            0, NULL, 0, 1, NULL, NULL, NULL,
            'Element warunkowy aktywowany po zleceniu lekarza.'
        ),
        (
            'BADANIE_LAB', 5, 'Badania laboratoryjne',
            0, NULL, 0, 1, NULL, NULL, NULL,
            'Element warunkowy aktywowany po zleceniu w Eskulapie.'
        ),
        (
            'BADANIE_GENETYCZNE', 6, 'Badania genetyczne',
            0, NULL, 0, 1, NULL, NULL, NULL,
            'Element warunkowy aktywowany po zleceniu w Eskulapie.'
        ),
        (
            'BADANIE_OBRAZOWE', 7, 'Badania obrazowe',
            0, NULL, 0, 1, NULL, NULL, NULL,
            'Element warunkowy aktywowany po zleceniu w Eskulapie.'
        ),
        (
            'KONSYLIUM', 8, 'Konsylium zespołu',
            1, 1, 1, 0, NULL, NULL, NULL,
            'Podsumowanie diagnostyki, wyników, diagnozy i zaleceń.'
        ),
        (
            'RAPORT_KONCOWY', 9,
            'Raport końcowy / plan dalszego postępowania',
            1, 1, 1, 0, 12, 'TYDZIEN', 'START_PROGRAMU',
            'Zakończenie ścieżki: raport i decyzja o dalszym postępowaniu.'
        )
) AS dane(
    kod_klocka,
    lp,
    nazwa,
    min_liczba,
    max_liczba,
    obowiazkowy,
    wymaga_zlecenia,
    termin_liczba,
    termin_jednostka,
    termin_od,
    opis
)
JOIN pk_klocki k ON k.kod = dane.kod_klocka
WHERE p.kod = 'ADHD_DZ_ML'
  AND s.kod = 'PODSTAWOWA'
ON CONFLICT DO NOTHING;

INSERT INTO pk_wyzwalacze(element_id, trigger_type, opis)
SELECT
    e.element_id,
    'START_EPIZODU',
    'Aktywacja przy rozpoczęciu epizodu.'
FROM pk_sciezka_elementy e
JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
JOIN pk_programy p ON p.program_id = s.program_id
JOIN pk_klocki k ON k.klocek_id = e.klocek_id
WHERE p.kod = 'ADHD_DZ_ML'
  AND s.kod = 'PODSTAWOWA'
  AND k.kod IN ('PKK_KWAL', 'WIZYTA_PSYCHIATRYCZNA')
  AND NOT EXISTS (
      SELECT 1
      FROM pk_wyzwalacze w
      WHERE w.element_id = e.element_id
        AND w.trigger_type = 'START_EPIZODU'
  );

INSERT INTO pk_wyzwalacze(
    element_id,
    trigger_type,
    trigger_element_id,
    opis
)
SELECT
    psycholog.element_id,
    'PO_ZAKONCZENIU',
    psychiatra.element_id,
    'Aktywacja po zakończeniu wizyty psychiatrycznej.'
FROM pk_sciezki s
JOIN pk_programy p ON p.program_id = s.program_id
JOIN pk_sciezka_elementy psycholog
    ON psycholog.sciezka_id = s.sciezka_id
JOIN pk_klocki k_psycholog
    ON k_psycholog.klocek_id = psycholog.klocek_id
JOIN pk_sciezka_elementy psychiatra
    ON psychiatra.sciezka_id = s.sciezka_id
JOIN pk_klocki k_psychiatra
    ON k_psychiatra.klocek_id = psychiatra.klocek_id
WHERE p.kod = 'ADHD_DZ_ML'
  AND s.kod = 'PODSTAWOWA'
  AND k_psycholog.kod = 'DIAGNOSTYKA_PSYCHOLOGICZNA'
  AND k_psychiatra.kod = 'WIZYTA_PSYCHIATRYCZNA'
  AND NOT EXISTS (
      SELECT 1
      FROM pk_wyzwalacze w
      WHERE w.element_id = psycholog.element_id
        AND w.trigger_type = 'PO_ZAKONCZENIU'
        AND w.trigger_element_id = psychiatra.element_id
  );

COMMIT;
