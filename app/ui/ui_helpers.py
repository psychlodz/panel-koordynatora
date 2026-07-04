from PySide6.QtWidgets import QDialogButtonBox, QMessageBox, QPushButton


STANDARD_BUTTON_TEXTS = {
    QDialogButtonBox.StandardButton.Save: "Zapisz",
    QDialogButtonBox.StandardButton.Cancel: "Anuluj",
    QDialogButtonBox.StandardButton.Close: "Zamknij",
    QDialogButtonBox.StandardButton.Ok: "OK",
}

STANDARD_BUTTON_TOOLTIPS = {
    QDialogButtonBox.StandardButton.Save: "Zapisz wprowadzone dane.",
    QDialogButtonBox.StandardButton.Cancel: "Anuluj zmiany i zamknij okno.",
    QDialogButtonBox.StandardButton.Close: "Zamknij okno.",
    QDialogButtonBox.StandardButton.Ok: "Zatwierdź wybór.",
}


def polish_dialog_buttons(button_box):
    for standard_button, text in STANDARD_BUTTON_TEXTS.items():
        button = button_box.button(standard_button)
        if button is not None:
            button.setText(text)
            button.setToolTip(STANDARD_BUTTON_TOOLTIPS[standard_button])


def create_help_button(parent, window_name, instruction):
    button = QPushButton("Pomoc")
    button.setProperty("role", "secondary")
    button.setToolTip(f"Pokaż instrukcję obsługi okna „{window_name}”.")
    button.clicked.connect(
        lambda: QMessageBox.information(
            parent,
            f"KOMPAS — Pomoc: {window_name}",
            instruction,
        )
    )
    return button


def ask_confirmation(parent, message, title="KOMPAS"):
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Question)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
    )
    dialog.setDefaultButton(QMessageBox.StandardButton.No)
    yes_button = dialog.button(QMessageBox.StandardButton.Yes)
    no_button = dialog.button(QMessageBox.StandardButton.No)
    yes_button.setText("Tak")
    yes_button.setToolTip("Potwierdź wykonanie operacji.")
    no_button.setText("Nie")
    no_button.setToolTip("Anuluj operację.")
    return dialog.exec() == QMessageBox.StandardButton.Yes
