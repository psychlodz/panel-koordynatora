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
    wp.wp_decyzja AS decyzja,
    wp.wp_program_leczenia AS program_leczenia,
    wp.wp_reskie_id AS eskierowanie_id,
    wp.wp_opis AS opis
FROM RI_OWNER.RI_WIZYTY_W_PORADNIACH wp
LEFT JOIN RI_OWNER.SZ_JEDNOSTKI_ORGANIZACYJNE jo
    ON jo.jo_jednostka_id = wp.wp_pr_poradnia_id
LEFT JOIN RI_OWNER.RI_PRACOWNICY pr
    ON pr.prac_pracownik_id = wp.wp_l_lekarz_id;
/

CREATE OR REPLACE VIEW ESK_RAPORTY.V_KOMPAS_WIZYTY_KWALIFIKACYJNE AS
WITH qualification_filter AS (
    SELECT
        CAST(NULL AS VARCHAR2(100)) AS typ_wizyty,
        CAST(NULL AS VARCHAR2(100)) AS procedura,
        CAST('PKK' AS VARCHAR2(100)) AS poradnia,
        CAST('KWALIF' AS VARCHAR2(100)) AS opis
    FROM dual
)
SELECT
    w.wizyta_id,
    w.pacjent_id,
    p.pesel,
    p.nazwisko,
    p.imie,
    w.data_wizyty,
    w.poradnia_id,
    w.poradnia_symbol,
    w.poradnia_nazwa AS poradnia,
    w.pracownik_id,
    w.pracownik,
    w.typ_wizyty,
    w.decyzja AS status_wizyty,
    w.opis
FROM ESK_RAPORTY.V_KOMPAS_WIZYTY w
JOIN ESK_RAPORTY.V_KOMPAS_PACJENCI p
    ON p.pacjent_id = w.pacjent_id
CROSS JOIN qualification_filter f
WHERE
    (
        f.typ_wizyty IS NOT NULL
        AND UPPER(NVL(w.typ_wizyty, '')) LIKE
            '%' || UPPER(f.typ_wizyty) || '%'
    )
    OR (
        f.poradnia IS NOT NULL
        AND (
            UPPER(NVL(w.poradnia_symbol, '')) LIKE
                '%' || UPPER(f.poradnia) || '%'
            OR UPPER(NVL(w.poradnia_nazwa, '')) LIKE
                '%' || UPPER(f.poradnia) || '%'
        )
    )
    OR (
        f.procedura IS NOT NULL
        AND UPPER(NVL(w.program_leczenia, '')) LIKE
            '%' || UPPER(f.procedura) || '%'
    )
    OR (
        f.opis IS NOT NULL
        AND UPPER(NVL(w.opis, '')) LIKE '%' || UPPER(f.opis) || '%'
    )
    -- TODO: dopasować filtry do rzeczywistego oznaczenia wizyty
    -- kwalifikacyjnej PKK w Eskulapie. Pole program_leczenia jest obecnie
    -- tymczasowym odpowiednikiem filtra procedury.
;
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
    s.skie_skierowanie_id AS badanie_skierowanie_id,
    s.skie_p_pacjent_id AS pacjent_id,
    COALESCE(
        s.skie_data_wystawienia_skie,
        s.skie_ins_date
    ) AS data_skierowania,
    s.skie_data_wystawienia AS data_proponowana,
    s.skie_plan_data_wyk AS data_planowana,
    s.skie_data_realizacji AS data_realizacji,
    s.skie_data_pobrania AS data_pobrania,
    s.skie_type AS typ,
    s.skie_stan_skierowania AS status,
    s.skie_pilne AS pilne,
    s.skie_tresc AS opis,
    s.skie_uwagi AS uwagi,
    s.skie_wam_wizyta_id AS wizyta_id,
    s.skie_pno_pobyt_id AS pobyt_id,
    s.skie_jo_jedn_wyst_id AS jednostka_wystawiajaca_id,
    s.skie_jo_jednostka_id AS jednostka_realizujaca_id,
    s.skie_prac_wystawil_id AS pracownik_wystawil_id,
    s.skie_prac_pracownik_id AS pracownik_realizujacy_id,
    s.skie_hist_bd_badanie_id AS badanie_id,
    b.bad_symbol AS badanie_symbol,
    COALESCE(b.bad_nazwa, s.skie_tresc) AS badanie_nazwa,
    b.bad_kod AS badanie_kod
FROM RI_OWNER.OD_SKIEROWANIA_NA_BADANIA s
LEFT JOIN LAB_OWNER.L_BADANIA b
    ON b.bad_badanie_id = s.skie_hist_bd_badanie_id
WHERE s.skie_p_pacjent_id IS NOT NULL;
/
