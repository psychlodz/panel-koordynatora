\set ON_ERROR_STOP on

-- Ten skrypt wykonuje administrator PostgreSQL (najczęściej użytkownik
-- postgres) podczas połączenia z bazą postgres.
-- Hasło nie jest zapisane w repozytorium: \password poprosi o nie bez echa.
SELECT 'CREATE ROLE kompas_app LOGIN'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'kompas_app'
)
\gexec

\password kompas_app

-- CREATE DATABASE nie może działać wewnątrz bloku transakcyjnego.
SELECT
    'CREATE DATABASE kompas OWNER kompas_app ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'kompas'
)
\gexec

GRANT CONNECT ON DATABASE kompas TO kompas_app;
