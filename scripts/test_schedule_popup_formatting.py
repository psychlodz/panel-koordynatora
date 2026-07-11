from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    service = read("app/services/schedule_service.py")
    plan = read("plan_pracy.py")

    require(
        '"\\n".join(' in service,
        "ScheduleService nie formatuje wielu rodzajów wizyt w osobnych liniach.",
    )
    require(
        'text.replace(";", "\\n").splitlines()' in plan,
        "Popup nie rozdziela wartości RODZAJE_WIZYT po średniku i nowej linii.",
    )
    require(
        '["PRACOWNIK", "GODZ_OD", "GODZ_DO"]' in plan,
        "Popup nie zachowuje jednego wiersza dla pracownika i zakresu godzin.",
    )
    require(
        'tbl.setHorizontalHeaderLabels(["Pracownik", "Godziny", "Rodzaje wizyt"])'
        in plan,
        "Popup nie ma oczekiwanych kolumn.",
    )
    require(
        "Qt.AlignLeft | Qt.AlignTop" in plan,
        "Kolumna rodzajów wizyt nie jest wyrównana do lewej i do góry.",
    )
    require(
        "tbl.resizeRowsToContents()" in plan,
        "Popup nie dopasowuje wysokości wierszy do listy rodzajów wizyt.",
    )

    print("OK: Popup harmonogramu pokazuje rodzaje wizyt w osobnych liniach.")


if __name__ == "__main__":
    main()
