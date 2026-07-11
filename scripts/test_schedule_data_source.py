from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VIEW = "ESK_RAPORTY.V_PLAN_PRACY_KALENDARZ"
REQUIRED_COLUMNS = [
    "JO_ID",
    "JO_SYMBOL",
    "JO_NAZWA",
    "DATA_DNIA",
    "DZIEN_TYG",
    "PRACOWNIK_ID",
    "PRACOWNIK",
    "GODZ_OD",
    "GODZ_DO",
    "PLN_ID",
]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    plan = read("plan_pracy.py")
    service = read("app/services/schedule_service.py")
    gateway = read("app/gateway/eskulap_gateway.py")
    repository = read("app/repositories/work_schedule_repository.py")
    config = read("config.py")
    config_example = read("config.example.ini")
    module_doc = read("docs/ARCHITECTURE/SCHEDULE_DATA_SOURCE.md")

    require(
        "ScheduleService" in plan,
        "plan_pracy.py nie korzysta z ScheduleService.",
    )
    require(
        "self.schedule_service.get_work_schedule" in plan,
        "Harmonogram nie pobiera planu przez ScheduleService.",
    )
    for forbidden in (
        "from db import create_connection",
        "import oracledb",
        "oracledb.connect",
        "V_PLAN_PRACY_KALENDARZ",
    ):
        require(
            forbidden not in plan,
            f"plan_pracy.py zawiera niedozwolone odwołanie: {forbidden}",
        )

    require(
        "self.gateway.get_work_schedule" in service,
        "ScheduleService nie deleguje pobrania harmonogramu do Gateway.",
    )
    require(
        "def get_work_schedule" in gateway,
        "EskulapGateway nie udostępnia metody get_work_schedule.",
    )
    require(
        "_work_schedule.list_work_schedule" in gateway,
        "EskulapGateway nie deleguje do repozytorium harmonogramu.",
    )
    require(
        "FROM {view_name} p" in repository,
        "Repozytorium harmonogramu nie korzysta ze skonfigurowanego widoku.",
    )
    require(
        "config.view_name" in repository,
        "Repozytorium harmonogramu nie czyta application.view_name.",
    )
    require(
        EXPECTED_VIEW in config,
        "config.py nie wskazuje domyślnego widoku harmonogramu.",
    )
    require(
        f"view_name={EXPECTED_VIEW}" in config_example,
        "config.example.ini nie wskazuje zatwierdzonego widoku harmonogramu.",
    )

    for column in REQUIRED_COLUMNS:
        require(
            f"p.{column}" in repository,
            f"Repozytorium harmonogramu nie pobiera kolumny {column}.",
        )
        require(
            column in module_doc,
            f"Dokumentacja źródła harmonogramu nie opisuje kolumny {column}.",
        )

    for doc_path in (
        "docs/API/ESKULAP_GATEWAY.md",
        "docs/DATABASE_ARCHITECTURE.md",
        "docs/ARCHITECTURE/KOMPAS_MODULE_ARCHITECTURE.md",
        "docs/ARCHITECTURE/SCHEDULE_DATA_SOURCE.md",
    ):
        text = read(doc_path)
        require(
            EXPECTED_VIEW in text,
            f"{doc_path} nie wskazuje widoku {EXPECTED_VIEW}.",
        )

    print("OK: Harmonogram korzysta z udokumentowanego źródła danych.")
    print(f"Widok Oracle: {EXPECTED_VIEW}")
    print("Przeplyw: UI -> ScheduleService -> EskulapGateway -> widok Oracle")


if __name__ == "__main__":
    main()
