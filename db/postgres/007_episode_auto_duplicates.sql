\set ON_ERROR_STOP on
SET client_encoding = 'UTF8';

BEGIN;

-- Aktualizacja constraintów dla automatycznych powieleń elementów epizodu.
-- Uruchom na bazie kompas jako właściciel tabel albo użytkownik postgres.

ALTER TABLE pk_epizod_elementy
DROP CONSTRAINT IF EXISTS ck_pk_epizod_elementy_origin;

ALTER TABLE pk_epizod_elementy
ADD CONSTRAINT ck_pk_epizod_elementy_origin
CHECK (
    typ_pochodzenia IN (
        'SCIEZKA',
        'POWIELENIE',
        'POWIELENIE_AUTOMATYCZNE',
        'RECZNIE'
    )
);

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
        'EDYCJA'
    )
);

-- Jeden rekord zdarzenia z Eskulapa może być przypisany tylko do jednego
-- zadania KOMPAS. Zapobiega to podwójnemu przypisaniu tej samej konsultacji
-- albo tego samego badania do wielu elementów epizodu.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_zadania_eskulap_event
ON pk_zadania(eskulap_system, eskulap_id)
WHERE eskulap_system IS NOT NULL
  AND eskulap_id IS NOT NULL;

COMMIT;
