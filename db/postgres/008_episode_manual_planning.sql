\set ON_ERROR_STOP on
SET client_encoding = 'UTF8';

BEGIN;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_data date;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_godz_od time;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_godz_do time;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_uwagi text;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_user_id text;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_created_at timestamptz;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS kompas_plan_updated_at timestamptz;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS eskulap_plan_data timestamptz;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS eskulap_plan_godz_od time;

ALTER TABLE pk_zadania
ADD COLUMN IF NOT EXISTS eskulap_plan_godz_do time;

ALTER TABLE pk_epizod_elementy_historia
DROP CONSTRAINT IF EXISTS ck_pk_epizod_elementy_hist_operation;

ALTER TABLE pk_epizod_elementy_historia
ADD CONSTRAINT ck_pk_epizod_elementy_hist_operation
CHECK (
    operacja IN (
        'UTWORZENIE',
        'POWIELENIE',
        'POWIELENIE_AUTOMATYCZNE',
        'DEZAKTYWACJA',
        'REAKTYWACJA',
        'EDYCJA',
        'PLANOWANIE_ELEMENTU',
        'ZMIANA_TERMINU_ELEMENTU',
        'USUNIECIE_TERMINU_ELEMENTU'
    )
);

COMMIT;
