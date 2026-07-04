from dataclasses import dataclass, field

from app.models.organizational_unit import OrganizationalUnit
from app.repositories.user_unit_repository import (
    list_user_units,
    set_default_unit,
)


def _unit_from_row(row):
    return OrganizationalUnit(
        jo_id=str(row["jo_id"]),
        jo_symbol=row.get("jo_symbol"),
        jo_nazwa=row.get("jo_nazwa"),
    )


@dataclass
class WorkContext:
    current_user: object | None = None
    current_unit: OrganizationalUnit | None = None
    user_units: list[OrganizationalUnit] = field(default_factory=list)

    def initialize(self, user):
        self.current_user = user
        rows = list_user_units(user.user_id)
        if rows and not any(row["is_default"] for row in rows):
            set_default_unit(user.user_id, rows[0]["jo_id"])
            rows[0]["is_default"] = 1
        self.user_units = [_unit_from_row(row) for row in rows]
        default = next(
            (row for row in rows if row["is_default"]),
            rows[0] if rows else None,
        )
        self.current_unit = (
            _unit_from_row(default)
            if default is not None
            else None
        )
        return self.current_unit

    def set_current_unit(self, unit_or_id):
        unit_id = str(
            unit_or_id.jo_id
            if isinstance(unit_or_id, OrganizationalUnit)
            else unit_or_id
        )
        unit = next(
            (
                candidate
                for candidate in self.user_units
                if candidate.jo_id == unit_id
            ),
            None,
        )
        if unit is None:
            raise ValueError(
                "Wybrana jednostka nie jest przypisana użytkownikowi"
            )
        self.current_unit = unit
        return unit

    def clear(self):
        self.current_user = None
        self.current_unit = None
        self.user_units = []


work_context = WorkContext()


def initialize_work_context(user):
    return work_context.initialize(user)


def set_current_unit(unit_or_id):
    return work_context.set_current_unit(unit_or_id)
