PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS pk_typy_elementow (
    typ_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pk_klocki (
    klocek_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    typ TEXT NOT NULL,
    opis TEXT,
    ikona TEXT,
    czy_aktywny INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

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
