\set ON_ERROR_STOP on

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

INSERT INTO pk_typy_elementow(kod, nazwa) VALUES
    ('PKK', 'Punkt konsultacyjno-koordynacyjny'),
    ('WIZYTA', 'Wizyta'),
    ('SESJA', 'Sesja terapeutyczna'),
    ('KONSULTACJA', 'Konsultacja specjalistyczna'),
    ('LAB', 'Badanie laboratoryjne'),
    ('GENETYKA', 'Badanie genetyczne'),
    ('OBRAZOWE', 'Badanie obrazowe'),
    ('KONSYLIUM', 'Konsylium'),
    ('RAPORT', 'Raport końcowy'),
    ('ZAMKNIECIE', 'Zamknięcie programu')
ON CONFLICT DO NOTHING;

INSERT INTO pk_klocki(kod, nazwa, typ, opis) VALUES
    (
        'KWALIFIKACJA',
        'Kwalifikacja',
        'PKK',
        'Kwalifikacja pacjenta do programu.'
    ),
    (
        'WIZYTA_KWALIFIKACYJNA_PKK',
        'Wizyta kwalifikacyjna w PKK',
        'PKK',
        'Wizyta kwalifikująca pacjenta do programu KOMPAS w punkcie PKK.'
    ),
    (
        'PKK',
        'Punkt konsultacyjno-koordynacyjny',
        'PKK',
        'Obsługa pacjenta w punkcie konsultacyjno-koordynacyjnym.'
    ),
    (
        'WIZYTA_PSYCHIATRYCZNA',
        'Wizyta psychiatryczna',
        'WIZYTA',
        'Wizyta diagnostyczna lub kontrolna u psychiatry.'
    ),
    (
        'DIAGNOSTYKA_PSYCHOLOGICZNA',
        'Diagnostyka psychologiczna',
        'WIZYTA',
        'Proces diagnostyki psychologicznej.'
    ),
    (
        'SESJA_TERAPEUTYCZNA',
        'Sesja terapeutyczna',
        'SESJA',
        'Pojedyncza sesja terapeutyczna.'
    ),
    (
        'PSYCHOTERAPIA',
        'Psychoterapia',
        'SESJA',
        'Cykl psychoterapii.'
    ),
    (
        'KONSULTACJA_SPECJALISTYCZNA',
        'Konsultacja specjalistyczna',
        'KONSULTACJA',
        'Konsultacja u wskazanego specjalisty.'
    ),
    (
        'BADANIE_LAB',
        'Badanie laboratoryjne',
        'LAB',
        'Badanie laboratoryjne zlecone w programie.'
    ),
    (
        'BADANIE_GENETYCZNE',
        'Badanie genetyczne',
        'GENETYKA',
        'Badanie genetyczne zlecone w programie.'
    ),
    (
        'BADANIE_OBRAZOWE',
        'Badanie obrazowe',
        'OBRAZOWE',
        'Badanie obrazowe zlecone w programie.'
    ),
    (
        'KONSYLIUM',
        'Konsylium',
        'KONSYLIUM',
        'Konsylium zespołu prowadzącego program.'
    ),
    (
        'RAPORT_KONCOWY',
        'Raport końcowy',
        'RAPORT',
        'Raport końcowy i plan dalszego postępowania.'
    ),
    (
        'ZAMKNIECIE_PROGRAMU',
        'Zamknięcie programu',
        'ZAMKNIECIE',
        'Formalne zakończenie udziału w programie.'
    )
ON CONFLICT DO NOTHING;

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
            'KWALIFIKACJA', 1, 'Kwalifikacja / PKK',
            1, 1, 1, 0, NULL::integer, NULL::text, NULL::text,
            'Początek organizacyjnej obsługi pacjenta w programie.'
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
  AND k.kod IN ('KWALIFIKACJA', 'WIZYTA_PSYCHIATRYCZNA')
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

