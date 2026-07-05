PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pk_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL COLLATE NOCASE UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (must_change_password IN (0, 1)),
    CHECK (is_active IN (0, 1)),
    CHECK (failed_login_count >= 0)
);

CREATE TABLE IF NOT EXISTS pk_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pk_user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY(user_id, role_id),
    FOREIGN KEY(user_id) REFERENCES pk_users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(role_id) REFERENCES pk_roles(role_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pk_user_units (
    user_id INTEGER NOT NULL,
    jo_id TEXT NOT NULL,
    jo_symbol TEXT,
    jo_nazwa TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, jo_id),
    FOREIGN KEY(user_id) REFERENCES pk_users(user_id) ON DELETE CASCADE,
    CHECK (is_default IN (0, 1))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_user_units_default
ON pk_user_units(user_id)
WHERE is_default = 1;

CREATE TABLE IF NOT EXISTS pk_programy (
    program_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    wersja TEXT,
    opis TEXT,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    data_od TEXT,
    data_do TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pk_program_units (
    program_id INTEGER NOT NULL,
    jo_id TEXT NOT NULL,
    jo_symbol TEXT,
    jo_nazwa TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(program_id, jo_id),
    FOREIGN KEY(program_id)
        REFERENCES pk_programy(program_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pk_sciezki (
    sciezka_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    kod TEXT NOT NULL,
    nazwa TEXT NOT NULL,
    opis TEXT,
    czy_aktywna INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    UNIQUE(program_id, kod),
    FOREIGN KEY(program_id) REFERENCES pk_programy(program_id)
);

CREATE TABLE IF NOT EXISTS pk_pathway_units (
    sciezka_id INTEGER NOT NULL,
    jo_id TEXT NOT NULL,
    jo_symbol TEXT,
    jo_nazwa TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(sciezka_id, jo_id),
    FOREIGN KEY(sciezka_id)
        REFERENCES pk_sciezki(sciezka_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pk_typy_elementow (
    typ_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    opis TEXT,
    kolejnosc INTEGER NOT NULL DEFAULT 0,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    czy_systemowy INTEGER NOT NULL DEFAULT 0,
    ikona TEXT,
    kolor TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (czy_aktywny IN (0, 1)),
    CHECK (czy_systemowy IN (0, 1)),
    CHECK (kolejnosc >= 0)
);

CREATE TABLE IF NOT EXISTS pk_grupy_klockow (
    grupa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    opis TEXT,
    kolejnosc INTEGER NOT NULL DEFAULT 0,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    czy_systemowy INTEGER NOT NULL DEFAULT 0,
    ikona TEXT,
    kolor TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (czy_aktywny IN (0, 1)),
    CHECK (czy_systemowy IN (0, 1)),
    CHECK (kolejnosc >= 0)
);

CREATE TABLE IF NOT EXISTS pk_jednostki_czasu (
    jednostka_czasu_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    opis TEXT,
    rodzaj_obliczenia TEXT NOT NULL,
    mnoznik INTEGER NOT NULL DEFAULT 1,
    kolejnosc INTEGER NOT NULL DEFAULT 0,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    czy_systemowy INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (rodzaj_obliczenia IN ('DNI', 'MIESIACE', 'LATA')),
    CHECK (mnoznik > 0),
    CHECK (kolejnosc >= 0),
    CHECK (czy_aktywny IN (0, 1)),
    CHECK (czy_systemowy IN (0, 1))
);

CREATE TABLE IF NOT EXISTS pk_klocki (
    klocek_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    opis TEXT,
    typ_elementu_id INTEGER NOT NULL,
    grupa_id INTEGER NOT NULL,
    ikona TEXT,
    kolor TEXT,
    domyslny_termin_liczba INTEGER,
    domyslna_jednostka_czasu_id INTEGER,
    czy_wymaga_zlecenia INTEGER NOT NULL DEFAULT 0,
    czy_obowiazkowy INTEGER NOT NULL DEFAULT 0,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    czy_systemowy INTEGER NOT NULL DEFAULT 0,
    kolejnosc INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(typ_elementu_id)
        REFERENCES pk_typy_elementow(typ_id),
    FOREIGN KEY(grupa_id)
        REFERENCES pk_grupy_klockow(grupa_id),
    FOREIGN KEY(domyslna_jednostka_czasu_id)
        REFERENCES pk_jednostki_czasu(jednostka_czasu_id),
    CHECK (
        domyslny_termin_liczba IS NULL
        OR domyslny_termin_liczba >= 0
    ),
    CHECK (
        (
            domyslny_termin_liczba IS NULL
            AND domyslna_jednostka_czasu_id IS NULL
        )
        OR
        (
            domyslny_termin_liczba IS NOT NULL
            AND domyslna_jednostka_czasu_id IS NOT NULL
        )
    ),
    CHECK (czy_wymaga_zlecenia IN (0, 1)),
    CHECK (czy_obowiazkowy IN (0, 1)),
    CHECK (czy_aktywny IN (0, 1)),
    CHECK (czy_systemowy IN (0, 1)),
    CHECK (kolejnosc >= 0)
);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_typ
ON pk_klocki(typ_elementu_id);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_grupa
ON pk_klocki(grupa_id);

CREATE INDEX IF NOT EXISTS idx_pk_klocki_jednostka_czasu
ON pk_klocki(domyslna_jednostka_czasu_id);

CREATE TABLE IF NOT EXISTS pk_sciezka_elementy (
    element_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sciezka_id INTEGER NOT NULL,
    klocek_id INTEGER NOT NULL,
    lp INTEGER NOT NULL,
    nazwa_w_sciezce TEXT NOT NULL,
    min_liczba INTEGER DEFAULT 0,
    max_liczba INTEGER,
    czy_obowiazkowy INTEGER NOT NULL DEFAULT 0,
    czy_wymaga_zlecenia INTEGER NOT NULL DEFAULT 0,
    termin_liczba INTEGER,
    termin_jednostka TEXT,
    termin_od TEXT,
    warunek_aktywacji TEXT,
    opis_organizacyjny TEXT,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(sciezka_id) REFERENCES pk_sciezki(sciezka_id),
    FOREIGN KEY(klocek_id) REFERENCES pk_klocki(klocek_id),
    UNIQUE(sciezka_id, lp)
);

CREATE TABLE IF NOT EXISTS pk_sciezka_zaleznosci (
    zaleznosc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sciezka_id INTEGER NOT NULL,
    element_od_id INTEGER NOT NULL,
    element_do_id INTEGER NOT NULL,
    typ TEXT NOT NULL CHECK (typ IN ('KOLEJNOSC', 'WARUNEK')),
    opis TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(sciezka_id) REFERENCES pk_sciezki(sciezka_id),
    FOREIGN KEY(element_od_id) REFERENCES pk_sciezka_elementy(element_id),
    FOREIGN KEY(element_do_id) REFERENCES pk_sciezka_elementy(element_id),
    CHECK (element_od_id <> element_do_id),
    UNIQUE(sciezka_id, element_od_id, element_do_id)
);

CREATE INDEX IF NOT EXISTS idx_pk_sciezka_zaleznosci_sciezka
ON pk_sciezka_zaleznosci(sciezka_id);

CREATE TABLE IF NOT EXISTS pk_wyzwalacze (
    trigger_id INTEGER PRIMARY KEY AUTOINCREMENT,
    element_id INTEGER NOT NULL,
    trigger_type TEXT NOT NULL CHECK (
        trigger_type IN (
            'START_EPIZODU',
            'PO_ZAKONCZENIU',
            'PO_ZLECENIU',
            'PO_WYNIKU',
            'RECZNIE'
        )
    ),
    trigger_element_id INTEGER,
    opis TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(element_id) REFERENCES pk_sciezka_elementy(element_id),
    FOREIGN KEY(trigger_element_id) REFERENCES pk_sciezka_elementy(element_id)
);

CREATE INDEX IF NOT EXISTS idx_pk_wyzwalacze_element
ON pk_wyzwalacze(element_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pk_wyzwalacze_start_epizodu
ON pk_wyzwalacze(element_id)
WHERE trigger_type = 'START_EPIZODU';

CREATE TABLE IF NOT EXISTS pk_epizody (
    epizod_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pacjent_id TEXT NOT NULL,
    program_id INTEGER,
    sciezka_id INTEGER,
    data_start TEXT,
    data_zakonczenia TEXT,
    status TEXT NOT NULL DEFAULT 'NOWY',
    koordynator_id TEXT,
    uwagi TEXT,
    source_system TEXT,
    source_type TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(program_id) REFERENCES pk_programy(program_id),
    FOREIGN KEY(sciezka_id) REFERENCES pk_sciezki(sciezka_id)
);

CREATE TABLE IF NOT EXISTS pk_zadania (
    zadanie_id INTEGER PRIMARY KEY AUTOINCREMENT,
    epizod_id INTEGER NOT NULL,
    element_id INTEGER,
    status TEXT NOT NULL DEFAULT 'DO_ZAPLANOWANIA',
    data_wymagana_do TEXT,
    data_zaplanowana TEXT,
    data_realizacji TEXT,
    zrodlo TEXT NOT NULL DEFAULT 'PROGRAM',
    eskulap_system TEXT,
    eskulap_id TEXT,
    uwagi TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(epizod_id) REFERENCES pk_epizody(epizod_id),
    FOREIGN KEY(element_id) REFERENCES pk_sciezka_elementy(element_id)
);

CREATE INDEX IF NOT EXISTS idx_pk_epizody_status
ON pk_epizody(status);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_status
ON pk_zadania(status);

CREATE INDEX IF NOT EXISTS idx_pk_zadania_epizod
ON pk_zadania(epizod_id);
