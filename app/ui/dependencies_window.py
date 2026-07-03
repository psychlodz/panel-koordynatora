from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.dependency_repository import (
    create_dependency,
    delete_dependency as remove_dependency,
    list_dependencies,
    update_dependency,
)
from app.repositories.pathway_repository import (
    get_pathway,
    list_pathway_elements,
)


class DependencyDialog(QDialog):
    def __init__(self, sciezka_id, dependency=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "KOMPAS — Edytuj zależność"
            if dependency
            else "KOMPAS — Dodaj zależność"
        )
        self.resize(620, 360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.previous_combo = QComboBox()
        self.next_combo = QComboBox()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["KOLEJNOSC", "WARUNEK"])
        self.description_edit = QTextEdit()

        elements = list_pathway_elements(sciezka_id)
        if len(elements) < 2:
            raise ValueError("Ścieżka musi mieć co najmniej dwa elementy")
        for element in elements:
            label = f"{element['lp']}. {element['nazwa_w_sciezce']} [{element['klocek_kod']}]"
            self.previous_combo.addItem(label, element["element_id"])
            self.next_combo.addItem(label, element["element_id"])

        form.addRow("Element poprzedni:", self.previous_combo)
        form.addRow("Element następny:", self.next_combo)
        form.addRow("Typ:", self.type_combo)
        form.addRow("Opis:", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if dependency is not None:
            previous_index = self.previous_combo.findData(
                dependency["element_od_id"]
            )
            next_index = self.next_combo.findData(dependency["element_do_id"])
            if previous_index >= 0:
                self.previous_combo.setCurrentIndex(previous_index)
            if next_index >= 0:
                self.next_combo.setCurrentIndex(next_index)
            self.type_combo.setCurrentText(dependency["typ"])
            self.description_edit.setPlainText(dependency["opis"] or "")
        elif self.next_combo.count() > 1:
            self.next_combo.setCurrentIndex(1)

    def accept(self):
        if self.previous_combo.currentData() == self.next_combo.currentData():
            QMessageBox.warning(
                self,
                "KOMPAS",
                "Element poprzedni i następny muszą być różne.",
            )
            return
        super().accept()

    def values(self) -> dict:
        return {
            "element_od_id": self.previous_combo.currentData(),
            "element_do_id": self.next_combo.currentData(),
            "typ": self.type_combo.currentText(),
            "opis": self.description_edit.toPlainText().strip() or None,
        }


class DependenciesWindow(QWidget):
    def __init__(self, sciezka_id):
        super().__init__()
        self.sciezka_id = sciezka_id
        self._dependencies_by_id = {}
        self.setWindowTitle("KOMPAS — Zależności")
        self.resize(980, 560)

        layout = QVBoxLayout(self)
        self.pathway_label = QLabel()
        self.pathway_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.pathway_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Element poprzedni", "Element następny", "Typ", "Opis"]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Dodaj")
        self.edit_button = QPushButton("Edytuj")
        self.delete_button = QPushButton("Usuń")
        self.refresh_button = QPushButton("Odśwież")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.add_button.clicked.connect(self.add_dependency)
        self.edit_button.clicked.connect(self.edit_dependency)
        self.delete_button.clicked.connect(self.delete_dependency)
        self.refresh_button.clicked.connect(lambda: self.refresh_dependencies())

        self.refresh_dependencies()

    def _show_error(self, message, exc):
        QMessageBox.critical(self, "KOMPAS", f"{message}: {exc}")

    def current_dependency_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh_dependencies(self):
        try:
            pathway = get_pathway(self.sciezka_id)
            if pathway is None:
                raise ValueError("Wybrana ścieżka nie istnieje")
            self.pathway_label.setText(
                f"Zależności ścieżki: {pathway['kod']} — {pathway['nazwa']}"
            )
            dependencies = list_dependencies(self.sciezka_id)
            self._dependencies_by_id = {
                dependency["zaleznosc_id"]: dependency
                for dependency in dependencies
            }
            self.table.setRowCount(len(dependencies))
            for row_index, dependency in enumerate(dependencies):
                previous = (
                    f"{dependency['element_od_lp']}. "
                    f"{dependency['element_od_nazwa']}"
                )
                following = (
                    f"{dependency['element_do_lp']}. "
                    f"{dependency['element_do_nazwa']}"
                )
                values = [
                    previous,
                    following,
                    dependency["typ"],
                    dependency["opis"] or "",
                ]
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column_index == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            dependency["zaleznosc_id"],
                        )
                    self.table.setItem(row_index, column_index, item)
        except Exception as exc:
            self._show_error("Nie udało się pobrać zależności", exc)

    def add_dependency(self):
        try:
            dialog = DependencyDialog(self.sciezka_id, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            create_dependency(self.sciezka_id, **dialog.values())
            self.refresh_dependencies()
        except Exception as exc:
            self._show_error("Nie udało się dodać zależności", exc)

    def edit_dependency(self):
        dependency_id = self.current_dependency_id()
        if dependency_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz zależność do edycji."
            )
            return
        dependency = self._dependencies_by_id.get(dependency_id)
        if dependency is None:
            self.refresh_dependencies()
            return
        try:
            dialog = DependencyDialog(
                self.sciezka_id, dependency=dependency, parent=self
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            update_dependency(dependency_id, **dialog.values())
            self.refresh_dependencies()
        except Exception as exc:
            self._show_error("Nie udało się zaktualizować zależności", exc)

    def delete_dependency(self):
        dependency_id = self.current_dependency_id()
        if dependency_id is None:
            QMessageBox.information(
                self, "KOMPAS", "Wybierz zależność do usunięcia."
            )
            return
        answer = QMessageBox.question(
            self, "KOMPAS", "Czy na pewno usunąć wybraną zależność?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            remove_dependency(dependency_id)
            self.refresh_dependencies()
        except Exception as exc:
            self._show_error("Nie udało się usunąć zależności", exc)
