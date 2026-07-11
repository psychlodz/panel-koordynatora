-- Widoki tylko do odczytu dla aplikacji KOMPAS.
-- Skrypt wykonuje administrator schematu ESK_RAPORTY.
-- Konto aplikacyjne powinno otrzymać wyłącznie uprawnienia SELECT.

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_PACJENCI AS
SELECT
    p.p_pacjent_id AS pacjent_id,
    p.p_nr_pesel AS pesel,
    p.p_nazwisko AS nazwisko,
    p.p_imie AS imie,
    p.p_drugie_imie AS drugie_imie,
    p.p_data_ur AS data_urodzenia,
    p.p_plec AS plec,
    p.p_telefon AS telefon,
    p.p_email AS email,
    p.p_rodz_imie AS opiekun_imie,
    p.p_rodz_nazw AS opiekun_nazwisko,
    p.p_rodz_nr_pesel AS opiekun_pesel,
    p.p_rodz_telefon AS opiekun_telefon,
    p.p_rodz_email AS opiekun_email,
    p.p_status AS status_pacjenta,
    p.p_data_zgonu AS data_zgonu
FROM RI_OWNER.RI_PACJENCI p
WHERE NVL(p.p_archiwum, 'N') <> 'T';
/

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_WIZYTY AS
SELECT
    wp.wp_wizyta_id AS wizyta_id,
    wp.wp_p_pacjent_id AS pacjent_id,
    wp.wp_pr_poradnia_id AS poradnia_id,
    jo.jo_symbol AS poradnia_symbol,
    jo.jo_nazwa AS poradnia_nazwa,
    wp.wp_l_lekarz_id AS pracownik_id,
    pr.prac_nazwisko || ' ' || pr.prac_imie AS pracownik,
    wp.wp_data_wizyty AS data_wizyty,
    wp.wp_data_wizyty_do AS data_wizyty_do,
    wp.wp_data_rejestracji AS data_rejestracji,
    wp.wp_typ_wizyty AS typ_wizyty,
    wp.wp_parametr AS parametr_kod,
    crc.rv_meaning AS parametr_nazwa,
    crc.rv_czy_aktualne AS parametr_czy_aktualne,
    wp.wp_decyzja AS decyzja,
    wp.wp_program_leczenia AS program_leczenia,
    wp.wp_reskie_id AS eskierowanie_id,
    wp.wp_opis AS opis
FROM RI_OWNER.RI_WIZYTY_W_PORADNIACH wp
LEFT JOIN RI_OWNER.SZ_JEDNOSTKI_ORGANIZACYJNE jo
    ON jo.jo_jednostka_id = wp.wp_pr_poradnia_id
LEFT JOIN RI_OWNER.RI_PRACOWNICY pr
    ON pr.prac_pracownik_id = wp.wp_l_lekarz_id
LEFT JOIN RI_OWNER.CG_REF_CODES crc
    ON crc.rv_domain = 'PARAMETRY'
   AND crc.rv_low_value = wp.wp_parametr;
/

-- TODO: jeżeli CG_REF_CODES nie znajduje się w schemacie RI_OWNER,
-- administrator powinien zastąpić powyższy JOIN wariantem:
-- LEFT JOIN CG_REF_CODES crc
--     ON crc.rv_domain = 'PARAMETRY'
--    AND crc.rv_low_value = wp.wp_parametr

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT AS
SELECT
    crc.rv_low_value AS parametr_kod,
    crc.rv_meaning AS parametr_nazwa,
    crc.rv_czy_aktualne AS czy_aktualne
FROM RI_OWNER.CG_REF_CODES crc
WHERE crc.rv_domain = 'PARAMETRY';
/

-- TODO: jeżeli CG_REF_CODES nie znajduje się w schemacie RI_OWNER,
-- należy odtworzyć widok pomocniczy z FROM CG_REF_CODES crc.

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ AS
WITH dni AS (
    SELECT TRUNC(SYSDATE) - 365 + LEVEL - 1 AS data_dnia
    FROM dual
    CONNECT BY LEVEL <= 365 * 3
),
warunki_szczegoly AS (
    SELECT DISTINCT
        plw.plw_pln_id,
        plw.plw_wp_parametr,
        NVL(pw.parametr_nazwa, plw.plw_wp_parametr) AS parametr_nazwa
    FROM RI_OWNER.RI_PLAN_PRACY_WARUNKI_NEW plw
    LEFT JOIN ESK_RAPORTY.V_KOMPAS_PARAMETRY_WIZYT pw
        ON pw.parametr_kod = plw.plw_wp_parametr
    WHERE plw.plw_wp_parametr IS NOT NULL
      AND NVL(plw.plw_typ, 'W') = 'W'
),
warunki AS (
    SELECT
        plw_pln_id,
        LISTAGG(plw_wp_parametr, ', ')
            WITHIN GROUP (
                ORDER BY plw_wp_parametr
            ) AS rodzaje_wizyt_kody,
        LISTAGG(parametr_nazwa, '; ')
            WITHIN GROUP (
                ORDER BY parametr_nazwa
            ) AS rodzaje_wizyt
    FROM warunki_szczegoly
    GROUP BY plw_pln_id
)
SELECT
    pln.pln_jo_jednostka_id AS jo_id,
    jo.jo_symbol AS jo_symbol,
    jo.jo_nazwa AS jo_nazwa,
    d.data_dnia AS data_dnia,
    TO_CHAR(d.data_dnia, 'YYYY-MM-DD') AS data_tekst,
    TO_CHAR(
        d.data_dnia,
        'DY',
        'NLS_DATE_LANGUAGE=POLISH'
    ) AS dzien_tyg,
    pln.pln_prac_pracownik_id AS pracownik_id,
    prac.prac_nazwisko || ' ' || prac.prac_imie AS pracownik,
    TO_CHAR(pln.pln_godz_od, 'HH24:MI') AS godz_od,
    TO_CHAR(pln.pln_godz_do, 'HH24:MI') AS godz_do,
    pln.pln_id AS pln_id,
    pln.pln_opis AS pln_opis,
    warunki.rodzaje_wizyt_kody AS rodzaje_wizyt_kody,
    warunki.rodzaje_wizyt AS rodzaje_wizyt
FROM RI_OWNER.RI_PLAN_PRACY_NEW pln
JOIN dni d
    ON d.data_dnia BETWEEN TRUNC(pln.pln_data_od)
                       AND TRUNC(NVL(pln.pln_data_do, d.data_dnia))
LEFT JOIN RI_OWNER.RI_PRACOWNICY prac
    ON prac.prac_pracownik_id = pln.pln_prac_pracownik_id
LEFT JOIN RI_OWNER.SZ_JEDNOSTKI_ORGANIZACYJNE jo
    ON jo.jo_jednostka_id = pln.pln_jo_jednostka_id
LEFT JOIN warunki
    ON warunki.plw_pln_id = pln.pln_id
WHERE NVL(pln.pln_czy_aktualny, 'T') = 'T'
  AND NVL(pln.pln_czy_wolne, 'N') = 'N'
  AND (
        (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 0
            AND NVL(pln.pln_po, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 1
            AND NVL(pln.pln_wt, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 2
            AND NVL(pln.pln_sr, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 3
            AND NVL(pln.pln_cz, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 4
            AND NVL(pln.pln_pi, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 5
            AND NVL(pln.pln_so, 'N') = 'T'
        )
     OR (
            TRUNC(d.data_dnia) - TRUNC(d.data_dnia, 'IW') = 6
            AND NVL(pln.pln_ni, 'N') = 'T'
        )
  );
/

-- Widok zgodności dla starej nazwy. Nazwa jest przestarzała i powinna zostać
-- usunięta ręcznie po potwierdzeniu działania V_KOMPAS_PLAN_PRACY_KALENDARZ.
CREATE OR REPLACE VIEW ESK_RAPORTY.V_PLAN_PRACY_KALENDARZ AS
SELECT *
FROM ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ;
/

-- Kontrakt KOMPAS wymaga kolumny DATA_KONSULTACJI.
-- Po zmianie SQL należy ręcznie wykonać poniższe CREATE OR REPLACE VIEW
-- w Oracle na koncie z uprawnieniami do schematu ESK_RAPORTY.
CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_KONSULTACJE AS
SELECT
    k.kon_konsultacja_id AS konsultacja_id,
    k.kon_p_pacjent_id AS pacjent_id,
    COALESCE(
        k.kon_data_przyjecia,
        k.kon_data_planowanej_kon,
        k.kon_data
    ) AS DATA_KONSULTACJI,
    k.kon_data AS data_wystawienia,
    k.kon_data_planowanej_kon AS data_planowana,
    k.kon_data_przyjecia AS data_przyjecia,
    k.kon_typ AS typ,
    k.kon_status AS status,
    k.kon_tryb AS tryb,
    k.kon_tytul AS tytul,
    k.kon_tekst AS opis,
    k.kon_uwagi AS uwagi,
    k.kon_wp_wizyta_id AS wizyta_id,
    k.kon_po_pobyt_id AS pobyt_id,
    k.kon_prac_wystawil_id AS pracownik_wystawil_id,
    k.kon_prac_obsluga_id AS pracownik_obsluga_id,
    k.kon_jo_obsluga_id AS jednostka_obsluga_id,
    k.kon_sp_specjalnosc_id AS specjalnosc_id
FROM RI_OWNER.OD_KONSULTACJE k
WHERE k.kon_p_pacjent_id IS NOT NULL;
/

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_BADANIA AS
SELECT
    skie.skie_skierowanie_id AS badanie_skierowanie_id,
    skie.skie_p_pacjent_id AS pacjent_id,
    skie.skie_data_wystawienia AS data_skierowania,
    skie.skie_plan_data_wyk AS data_planowana_wykonania,
    skie.skie_plan_data_wyk AS data_zaplanowana,
    skie.skie_data_pobrania AS data_pobrania,
    skie.skie_data_realizacji AS data_realizacji,
    skie.skie_type AS typ,
    skie.skie_stan_skierowania AS status,
    skie.skie_pilne AS pilne,
    skie.skie_tresc AS opis,
    skie.skie_uwagi AS uwagi,
    skie.skie_wam_wizyta_id AS wizyta_id,
    skie.skie_pno_pobyt_id AS pobyt_id,
    skie.skie_jo_jedn_wyst_id AS jednostka_wystawiajaca_id,
    skie.skie_jo_jednostka_id AS jednostka_realizujaca_id,
    skie.skie_prac_wystawil_id AS pracownik_wystawil_id,
    skie.skie_prac_pracownik_id AS pracownik_realizujacy_id,
    skie.skie_hist_bd_badanie_id AS badanie_id,
    b.bad_symbol AS badanie_symbol,
    COALESCE(b.bad_nazwa, skie.skie_tresc) AS badanie_nazwa,
    b.bad_kod AS badanie_kod
FROM RI_OWNER.OD_SKIEROWANIA_NA_BADANIA skie
LEFT JOIN LAB_OWNER.L_BADANIA b
    ON b.bad_badanie_id = skie.skie_hist_bd_badanie_id
WHERE skie.skie_p_pacjent_id IS NOT NULL;
/
