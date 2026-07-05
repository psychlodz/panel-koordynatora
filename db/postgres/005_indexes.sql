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

CREATE INDEX IF NOT EXISTS idx_pk_klocki_grupa
ON pk_klocki(grupa_id);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_jednostka_czasu
ON pk_klocki(domyslna_jednostka_czasu_id);

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

CREATE INDEX IF NOT EXISTS idx_pk_zadania_status
ON pk_zadania(status);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_epizod
ON pk_zadania(epizod_id);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_element
ON pk_zadania(element_id);

COMMIT;
