\set ON_ERROR_STOP on
SET client_encoding = 'UTF8';

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_users_login_nocase
ON pk_users(lower(login));

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_roles_code_nocase
ON pk_roles(lower(code));

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_user_units_default
ON pk_user_units(user_id)
WHERE is_default = 1;

CREATE INDEX IF NOT EXISTS idx_pk_program_units_jo
ON pk_program_units(jo_id);

CREATE INDEX IF NOT EXISTS idx_pk_pathway_units_jo
ON pk_pathway_units(jo_id);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_typ
ON pk_klocki(typ_elementu_id);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_jednostka_czasu
ON pk_klocki(domyslna_jednostka_czasu_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_rodzaje_wizyt_code_nocase
ON pk_rodzaje_wizyt_eskulap(lower(parametr_kod));

CREATE INDEX IF NOT EXISTS idx_pk_rodzaje_wizyt_current
ON pk_rodzaje_wizyt_eskulap(czy_aktualny_eskulap);

CREATE INDEX IF NOT EXISTS idx_pk_rodzaje_wizyt_kompas_active
ON pk_rodzaje_wizyt_eskulap(czy_aktywny_kompas);

CREATE INDEX IF NOT EXISTS idx_pk_mapowanie_wizyt_klocek
ON pk_mapowanie_wizyt(klocek_id);

CREATE INDEX IF NOT EXISTS idx_pk_mapowanie_wizyt_rodzaj
ON pk_mapowanie_wizyt(rodzaj_wizyty_id);

CREATE INDEX IF NOT EXISTS idx_pk_mapowanie_wizyt_active
ON pk_mapowanie_wizyt(czy_aktywne);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_mapowanie_wizyt_active_rodzaj
ON pk_mapowanie_wizyt(rodzaj_wizyty_id)
WHERE czy_aktywne = 1;

CREATE INDEX IF NOT EXISTS idx_pk_sciezka_elementy_sciezka
ON pk_sciezka_elementy(sciezka_id);

CREATE INDEX IF NOT EXISTS idx_pk_sciezka_zaleznosci_sciezka
ON pk_sciezka_zaleznosci(sciezka_id);

CREATE INDEX IF NOT EXISTS idx_pk_wyzwalacze_element
ON pk_wyzwalacze(element_id);

CREATE INDEX IF NOT EXISTS idx_pk_wyzwalacze_source
ON pk_wyzwalacze(trigger_element_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_wyzwalacze_start_epizodu
ON pk_wyzwalacze(element_id)
WHERE trigger_type = 'START_EPIZODU';

CREATE INDEX IF NOT EXISTS idx_pk_epizody_status
ON pk_epizody(status);

CREATE INDEX IF NOT EXISTS idx_pk_epizody_patient
ON pk_epizody(pacjent_id_eskulap);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_epizody_source
ON pk_epizody(source_system, source_type, source_id)
WHERE source_system IS NOT NULL
  AND source_type IS NOT NULL
  AND source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pk_epizod_elementy_epizod
ON pk_epizod_elementy(epizod_id);

CREATE INDEX IF NOT EXISTS idx_pk_epizod_elementy_sciezka_element
ON pk_epizod_elementy(sciezka_element_id);

CREATE INDEX IF NOT EXISTS idx_pk_epizod_elementy_source
ON pk_epizod_elementy(element_zrodlowy_id);

CREATE INDEX IF NOT EXISTS idx_pk_epizod_elementy_hist_element
ON pk_epizod_elementy_historia(epizod_element_id);

CREATE INDEX IF NOT EXISTS idx_pk_epizod_elementy_hist_episode
ON pk_epizod_elementy_historia(epizod_id);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_status
ON pk_zadania(status);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_epizod
ON pk_zadania(epizod_id);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_element
ON pk_zadania(element_id);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_epizod_element
ON pk_zadania(epizod_element_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_zadania_eskulap_event
ON pk_zadania(eskulap_system, eskulap_id)
WHERE eskulap_system IS NOT NULL
  AND eskulap_id IS NOT NULL;

COMMIT;
