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
    ('KONSULTACJA', 'Konsultacja', NULL, 40, 1, 1),
    ('BADANIE_LAB', 'Badanie laboratoryjne', NULL, 50, 1, 1),
    ('BADANIE_GEN', 'Badanie genetyczne', NULL, 60, 1, 1),
    ('BADANIE_OBRAZOWE', 'Badanie obrazowe', NULL, 70, 1, 1),
    ('KONSYLIUM', 'Konsylium', NULL, 80, 1, 1),
    ('SUPERWIZJA', 'Superwizja', NULL, 90, 1, 1),
    ('ZAKONCZENIE', 'Zakończenie programu', NULL, 110, 1, 1)
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
    kod, nazwa, opis, typ_elementu_id, ikona, kolor,
    kolor_tekstu,
    domyslny_termin_liczba, domyslna_jednostka_czasu_id,
    czy_wymaga_zlecenia, czy_obowiazkowy, czy_aktywny,
    czy_systemowy, kolejnosc
)
SELECT
    dane.kod, dane.nazwa, dane.opis, typ.typ_id,
    dane.ikona, dane.kolor,
    CASE
        WHEN dane.typ_kod IN ('BADANIE_LAB', 'SUPERWIZJA')
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
            'PKK', 'PKK', '#173F5F', 0, 1, 10
        ),
        (
            'PKK_WIZ', 'Wizyta w PKK',
            'Wizyta lub czynność organizacyjna realizowana w PKK w trakcie programu.',
            'PKK', 'PKK', '#2F80ED', 0, 0, 20
        ),
        (
            'KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA',
            'Konsultacja psychiatryczna kompleksowa',
            'Kompleksowa konsultacja psychiatryczna w programie.',
            'WIZYTA', 'PSY', '#2F80ED', 0, 1, 30
        ),
        (
            'KONSULTACJA_PSYCHIATRYCZNA_DIAGNOSTYCZNA',
            'Konsultacja psychiatryczna diagnostyczna',
            'Konsultacja psychiatryczna służąca diagnostyce pacjenta.',
            'WIZYTA', 'PSY', '#2F80ED', 0, 0, 40
        ),
        (
            'KONSULTACJA_PSYCHIATRYCZNA_TERAPEUTYCZNA',
            'Konsultacja psychiatryczna terapeutyczna',
            'Konsultacja psychiatryczna ukierunkowana terapeutycznie.',
            'WIZYTA', 'PSY', '#2F80ED', 0, 0, 50
        ),
        (
            'KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA',
            'Konsultacja psychologiczna diagnostyczna',
            'Konsultacja psychologiczna służąca diagnostyce pacjenta.',
            'WIZYTA', 'PSY', '#F2C94C', 0, 0, 60
        ),
        (
            'KONSULTACJA_PSYCHOLOGICZNA_TERAPEUTYCZNA',
            'Konsultacja psychologiczna terapeutyczna',
            'Konsultacja psychologiczna ukierunkowana terapeutycznie.',
            'WIZYTA', 'PSY', '#2F80ED', 0, 0, 70
        ),
        (
            'KONSULTACJA_TERAPEUTY_SRODOWISKOWEGO',
            'Konsultacja terapeuty środowiskowego',
            'Konsultacja terapeuty środowiskowego wspierająca realizację programu.',
            'WIZYTA', 'TER', '#2F80ED', 0, 0, 80
        ),
        (
            'KONSULTACJA_PSYCHOTERAPEUTYCZNA_DIAGNOSTYCZNA',
            'Konsultacja psychoterapeutyczna diagnostyczna',
            'Konsultacja psychoterapeutyczna służąca diagnostyce pacjenta.',
            'WIZYTA', 'PST', '#2F80ED', 0, 0, 90
        ),
        (
            'KONSULTACJA_PSYCHOTERAPEUTYCZNA_TERAPEUTYCZNA',
            'Konsultacja psychoterapeutyczna terapeutyczna',
            'Konsultacja psychoterapeutyczna ukierunkowana terapeutycznie.',
            'WIZYTA', 'PST', '#2F80ED', 0, 0, 100
        ),
        (
            'SUPERWIZJA', 'Superwizja',
            'Superwizja procesu terapeutycznego lub diagnostycznego.',
            'SUPERWIZJA', 'SUP', '#F2C94C', 0, 0, 110
        ),
        (
            'SESJA_TERAPEUTYCZNA', 'Sesja terapeutyczna',
            'Pojedyncza sesja terapeutyczna.',
            'WIZYTA', 'SES', '#27AE60', 0, 0, 120
        ),
        (
            'SESJA_TERAPEUTYCZNA_GRUPOWA', 'Sesja terapeutyczna grupowa',
            'Grupowa sesja terapeutyczna.',
            'WIZYTA', 'SGR', '#27AE60', 0, 0, 130
        ),
        (
            'SESJA_PSYCHOLOGICZNA', 'Sesja psychologiczna',
            'Indywidualna sesja psychologiczna.',
            'WIZYTA', 'SPS', '#27AE60', 0, 0, 140
        ),
        (
            'SESJA_PSYCHOLOGICZNA_GRUPOWA', 'Sesja psychologiczna grupowa',
            'Grupowa sesja psychologiczna.',
            'WIZYTA', 'SPG', '#27AE60', 0, 0, 150
        ),
        (
            'SESJA_PSYCHOTERAPEUTYCZNA', 'Sesja psychoterapeutyczna',
            'Indywidualna sesja psychoterapeutyczna.',
            'WIZYTA', 'SPT', '#27AE60', 0, 0, 160
        ),
        (
            'SESJA_PSYCHOTERAPEUTYCZNA_GRUPOWA',
            'Sesja psychoterapeutyczna grupowa',
            'Grupowa sesja psychoterapeutyczna; zastępuje ogólny klocek PSYCHOTERAPIA.',
            'WIZYTA', 'SPG', '#27AE60', 0, 0, 170
        ),
        (
            'KONSULTACJA_SPECJALISTYCZNA', 'Konsultacja specjalistyczna',
            'Konsultacja u wskazanego specjalisty.',
            'KONSULTACJA', 'KON', '#7B2CBF', 1, 0, 180
        ),
        (
            'BADANIA_LABORATORYJNE', 'Badania laboratoryjne',
            'Badania laboratoryjne zlecone w programie.',
            'BADANIE_LAB', 'LAB', '#F2994A', 1, 0, 190
        ),
        (
            'BADANIA_GENETYCZNE', 'Badania genetyczne',
            'Badania genetyczne zlecone w programie.',
            'BADANIE_GEN', 'GEN', '#F2C94C', 1, 0, 200
        ),
        (
            'BADANIE_OBRAZOWE', 'Badanie obrazowe',
            'Badanie obrazowe zlecone w programie.',
            'BADANIE_OBRAZOWE', 'OBR', '#1BA39C', 1, 0, 210
        ),
        (
            'KONSYLIUM', 'Konsylium',
            'Konsylium zespołu prowadzącego program.',
            'KONSYLIUM', 'KON', '#1B365D', 0, 1, 220
        ),
        (
            'ZAKONCZENIE_PROGRAMU', 'Zakończenie programu',
            'Formalne zakończenie udziału w programie.',
            'ZAKONCZENIE', 'KON', '#1F6B45', 0, 1, 230
        )
) AS dane(
    kod, nazwa, opis, typ_kod, ikona, kolor,
    wymaga_zlecenia, obowiazkowy, kolejnosc
)
JOIN pk_typy_elementow typ ON typ.kod = dane.typ_kod
ON CONFLICT DO NOTHING;

INSERT INTO pk_rodzaje_wizyt_eskulap(
    parametr_kod,
    parametr_nazwa,
    czy_aktualny_eskulap,
    czy_aktywny_kompas,
    last_seen_at,
    synchronized_at
)
VALUES (
    'F18',
    'Wizyta kwalifikacyjna PKK',
    1,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (parametr_kod) DO UPDATE
SET parametr_nazwa = EXCLUDED.parametr_nazwa,
    czy_aktualny_eskulap = EXCLUDED.czy_aktualny_eskulap,
    czy_aktywny_kompas = EXCLUDED.czy_aktywny_kompas,
    last_seen_at = EXCLUDED.last_seen_at,
    synchronized_at = EXCLUDED.synchronized_at,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO pk_mapowanie_wizyt(
    klocek_id,
    rodzaj_wizyty_id,
    czy_aktywne
)
SELECT
    k.klocek_id,
    r.rodzaj_wizyty_id,
    1
FROM pk_klocki k
JOIN pk_rodzaje_wizyt_eskulap r
    ON r.parametr_kod = 'F18'
WHERE k.kod = 'PKK_KWAL'
ON CONFLICT (klocek_id, rodzaj_wizyty_id) DO UPDATE
SET klocek_id = EXCLUDED.klocek_id,
    rodzaj_wizyty_id = EXCLUDED.rodzaj_wizyty_id,
    czy_aktywne = EXCLUDED.czy_aktywne,
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
            'KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA', 2,
            'Konsultacja psychiatryczna kompleksowa',
            1, 3, 1, 0, NULL, NULL, NULL,
            'Do 3 kompleksowych konsultacji psychiatrycznych w programie.'
        ),
        (
            'KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA', 3,
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
            'BADANIA_LABORATORYJNE', 5, 'Badania laboratoryjne',
            0, NULL, 0, 1, NULL, NULL, NULL,
            'Element warunkowy aktywowany po zleceniu w Eskulapie.'
        ),
        (
            'BADANIA_GENETYCZNE', 6, 'Badania genetyczne',
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
            'ZAKONCZENIE_PROGRAMU', 9,
            'Zakończenie programu / plan dalszego postępowania',
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
  AND k.kod IN ('PKK_KWAL', 'KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA')
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
  AND k_psycholog.kod = 'KONSULTACJA_PSYCHOLOGICZNA_DIAGNOSTYCZNA'
  AND k_psychiatra.kod = 'KONSULTACJA_PSYCHIATRYCZNA_KOMPLEKSOWA'
  AND NOT EXISTS (
      SELECT 1
      FROM pk_wyzwalacze w
      WHERE w.element_id = psycholog.element_id
        AND w.trigger_type = 'PO_ZAKONCZENIU'
        AND w.trigger_element_id = psychiatra.element_id
  );

COMMIT;
