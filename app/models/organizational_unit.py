from dataclasses import dataclass


@dataclass(frozen=True)
class OrganizationalUnit:
    jo_id: str
    jo_symbol: str | None = None
    jo_nazwa: str | None = None

    @property
    def display_name(self):
        description = " — ".join(
            value
            for value in (self.jo_symbol, self.jo_nazwa)
            if value
        )
        return (
            f"{description} [{self.jo_id}]"
            if description
            else f"Jednostka [{self.jo_id}]"
        )
