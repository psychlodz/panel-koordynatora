import configparser
import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    database_user: str
    database_password: str
    database_dsn: str
    default_jo_id: str
    default_months: int
    slot_minutes: int
    hour_start: int
    hour_end: int
    view_name: str


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config() -> AppConfig:
    config_path = os.path.join(app_dir(), "config.ini")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Brak pliku konfiguracyjnego: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    required_database_fields = ("user", "password", "dsn")
    missing_fields = [
        f"database.{field}"
        for field in required_database_fields
        if not parser.get("database", field, fallback="").strip()
    ]
    if missing_fields:
        raise ValueError(
            "Brak wymaganych pól konfiguracji: " + ", ".join(missing_fields)
        )

    return AppConfig(
        database_user=parser.get("database", "user"),
        database_password=parser.get("database", "password"),
        database_dsn=parser.get("database", "dsn"),
        default_jo_id=parser.get(
            "application", "default_jo_id", fallback="249"
        ),
        default_months=parser.getint(
            "application", "default_months", fallback=3
        ),
        slot_minutes=parser.getint(
            "application", "slot_minutes", fallback=180
        ),
        hour_start=parser.getint("application", "hour_start", fallback=7),
        hour_end=parser.getint("application", "hour_end", fallback=22),
        view_name=parser.get(
            "application",
            "view_name",
            fallback="ESK_RAPORTY.V_KOMPAS_PLAN_PRACY_KALENDARZ",
        ),
    )
