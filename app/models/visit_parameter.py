from dataclasses import dataclass


@dataclass(frozen=True)
class VisitParameter:
    code: str
    name: str | None = None
    is_active: str | int | bool | None = None
