BLOCK_GROUP_COLORS = {
    "KWALIFIKACJA": ("#173F5F", "#FFFFFF"),
    "WIZYTY": ("#2F80ED", "#FFFFFF"),
    "KONSULTACJE": ("#7B2CBF", "#FFFFFF"),
    "BADANIA_LAB": ("#F2994A", "#1F2937"),
    "BADANIA_OBRAZOWE": ("#1BA39C", "#FFFFFF"),
    "DIAGNOSTYKA": ("#F2C94C", "#1F2937"),
    "PSYCHOTERAPIA": ("#27AE60", "#FFFFFF"),
    "DOKUMENTACJA": ("#828282", "#FFFFFF"),
    "RAPORTY": ("#1B365D", "#FFFFFF"),
    "ZAKONCZENIE_PROGRAMU": ("#1F6B45", "#FFFFFF"),
}

TASK_STATUS_COLORS = {
    "PO_TERMINIE": ("#C62828", "#FFFFFF"),
    "DO_ZAPLANOWANIA": ("#F2994A", "#1F2937"),
    "ZAPLANOWANO": ("#2F80ED", "#FFFFFF"),
    "ZAPLANOWANE": ("#2F80ED", "#FFFFFF"),
    "W_REALIZACJI": ("#1BA39C", "#FFFFFF"),
    "ZREALIZOWANO": ("#27AE60", "#FFFFFF"),
    "ZREALIZOWANE": ("#27AE60", "#FFFFFF"),
    "ANULOWANO": ("#828282", "#FFFFFF"),
    "ANULOWANE": ("#828282", "#FFFFFF"),
}


def task_status_colors(status, overdue=False):
    key = "PO_TERMINIE" if overdue else str(status or "").strip().upper()
    return TASK_STATUS_COLORS.get(key)


__all__ = [
    "BLOCK_GROUP_COLORS",
    "TASK_STATUS_COLORS",
    "task_status_colors",
]
