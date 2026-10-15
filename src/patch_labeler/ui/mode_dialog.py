from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class ModeDialog(QDialog):
    """Диалог выбора режима работы при запуске."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patch Labeler — выбор режима")
        self.setFixedSize(440, 260)

        self.selected_mode = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Выберите режим работы")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("От режима зависит, какие папки и файлы нужно указать.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.btn_labeling = QPushButton("Разметка\n(снимки → патчи + разметка)")
        self.btn_labeling.setMinimumHeight(56)
        self.btn_labeling.setToolTip(
            "Понадобятся: входная папка со снимками и выходная папка.\n"
            "labels.json будет создан автоматически в выходной папке."
        )
        self.btn_labeling.clicked.connect(lambda: self._choose("labeling"))
        layout.addWidget(self.btn_labeling)

        self.btn_view = QPushButton("Просмотр разметки\n(снимки + JSON)")
        self.btn_view.setMinimumHeight(56)
        self.btn_view.setToolTip(
            "Понадобятся: папка со снимками и файл JSON с разметкой.\n"
            "Режим только для чтения: ничего не сохраняется на диск."
        )
        self.btn_view.clicked.connect(lambda: self._choose("view"))
        layout.addWidget(self.btn_view)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel)

    def _choose(self, mode):
        self.selected_mode = mode
        self.accept()


def choose_mode(parent=None):
    """
    Возвращает "labeling", "view" или None (если пользователь отменил).
    """
    dialog = ModeDialog(parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_mode