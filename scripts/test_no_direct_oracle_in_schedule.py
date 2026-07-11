from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES_TO_CHECK = [
    ROOT / "plan_pracy.py",
    ROOT / "calendar_logic.py",
    ROOT / "app" / "services" / "schedule_service.py",
]
FILES_TO_CHECK.extend((ROOT / "app" / "ui").glob("*schedule*.py"))
FILES_TO_CHECK.extend((ROOT / "app" / "ui").glob("*calendar*.py"))

FORBIDDEN_PATTERNS = [
    "import oracledb",
    "oracledb.connect",
    "from db import create_connection",
    "V_PLAN_PRACY_KALENDARZ",
]


def main():
    problems = []
    for path in sorted(set(FILES_TO_CHECK)):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                problems.append((path.relative_to(ROOT), pattern))

    if problems:
        print("Wykryto bezpośrednie odwołania harmonogramu do Oracle:")
        for path, pattern in problems:
            print(f"- {path}: {pattern}")
        raise SystemExit(1)

    print("OK: Harmonogram/UI nie zawiera bezpośrednich odwołań do Oracle.")


if __name__ == "__main__":
    main()
