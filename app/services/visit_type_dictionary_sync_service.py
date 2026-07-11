import logging

from app.gateway.eskulap_gateway import EskulapGateway
from app.repositories.db_connection import create_connection
from app.repositories.visit_type_dictionary_repository import (
    deactivate_missing,
    upsert_from_eskulap,
)


logger = logging.getLogger(__name__)


class VisitTypeDictionarySyncService:
    def __init__(self, gateway=None):
        self.gateway = gateway or EskulapGateway()

    def synchronize(self) -> dict:
        logger.info("START_SYNC_RODZAJE_WIZYT")
        records = self.gateway.list_visit_parameters(only_active=False)
        if not records:
            logger.warning("Słownik rodzajów wizyt z Eskulapa jest pusty")

        connection = create_connection()
        try:
            with connection:
                stats = upsert_from_eskulap(records, connection=connection)
                missing_count = deactivate_missing(
                    stats["seen_codes"],
                    connection=connection,
                )
            summary = {
                "pobrano": len(records),
                "dodano": stats["added"],
                "zaktualizowano": stats["updated"],
                "bez_zmian": stats["unchanged"],
                "oznaczono_jako_nieaktualne": missing_count,
            }
            logger.info("SYNC_RODZAJE_WIZYT_OK %s", summary)
            return summary
        except Exception:
            logger.exception("SYNC_RODZAJE_WIZYT_ROLLBACK")
            raise
        finally:
            connection.close()


def synchronize_visit_type_dictionary() -> dict:
    return VisitTypeDictionarySyncService().synchronize()


__all__ = [
    "VisitTypeDictionarySyncService",
    "synchronize_visit_type_dictionary",
]
