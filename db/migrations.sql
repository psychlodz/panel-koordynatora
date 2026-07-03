-- Idempotent data migrations executed for new and existing databases.

-- T2-E1: local users and roles.
INSERT OR IGNORE INTO pk_roles(code, name) VALUES
('ADMIN', 'Administrator'),
('KOORDYNATOR', 'Koordynator'),
('KIEROWNIK', 'Kierownik');

INSERT OR IGNORE INTO pk_users(
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
);

INSERT OR IGNORE INTO pk_user_roles(user_id, role_id)
SELECT u.user_id, r.role_id
FROM pk_users u, pk_roles r
WHERE u.login = 'admin'
  AND r.code = 'ADMIN';

-- S8-E1: initial task triggers for the ADHD pathway.
INSERT OR IGNORE INTO pk_wyzwalacze(element_id, trigger_type, opis)
SELECT e.element_id, 'START_EPIZODU', 'Aktywacja przy rozpoczęciu epizodu.'
FROM pk_sciezka_elementy e
JOIN pk_sciezki s ON s.sciezka_id = e.sciezka_id
JOIN pk_programy p ON p.program_id = s.program_id
JOIN pk_klocki k ON k.klocek_id = e.klocek_id
WHERE p.kod = 'ADHD_DZ_ML'
  AND s.kod = 'PODSTAWOWA'
  AND k.kod IN ('KWALIFIKACJA', 'WIZYTA_PSYCHIATRYCZNA');

INSERT INTO pk_wyzwalacze(
    element_id, trigger_type, trigger_element_id, opis
)
SELECT psycholog.element_id,
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
