import logging
import os
from datetime import datetime

import pandas as pd
from PySide6.QtWidgets import QFileDialog, QMessageBox


def export_table_to_excel(parent, table, export_dir: str):
    try:
        if table.rowCount() == 0 or table.columnCount() == 0:
            QMessageBox.information(parent, "Eksport", "Brak danych do eksportu.")
            return

        default_name = os.path.join(export_dir, f"plan_pracy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        path, _ = QFileDialog.getSaveFileName(parent, "Zapisz jako", default_name, "Excel (*.xlsx)")
        if not path:
            return

        rows = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
        cols = [table.horizontalHeaderItem(c).text().replace("\n", " ") for c in range(table.columnCount())]
        data = []
        for r in range(table.rowCount()):
            row = []
            for c in range(table.columnCount()):
                item = table.item(r, c)
                row.append(item.text() if item else "")
            data.append(row)

        out = pd.DataFrame(data, index=rows, columns=cols)
        out.to_excel(path)
        QMessageBox.information(parent, "Eksport", "Plik Excel został utworzony.")
    except Exception as exc:
        logging.exception("Błąd eksportu Excel")
        QMessageBox.critical(parent, "Błąd", f"Nie udało się wyeksportować danych:\n\n{exc}")
