from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QAbstractItemView,
)


class ImageListPanel(QWidget):
    """Панель со списком снимков."""

    image_selected = Signal(int)

    STATUS_MARKERS = {
        "full": "[+]",
        "partly": "[!]",
        "skipped": "[->]",
        "none": "",
    }

    STATUS_COLORS = {
        "full": (90, 180, 90),
        "partly": (230, 160, 60),
        "skipped": (140, 140, 140),
        "none": None,
    }

    def __init__(self, parent=None, mode="labeling"):
        super().__init__(parent)

        self._view_mode = (mode == "view")
        self._names = []
        self._rows = {}
        self._statuses = {}
        self._current_row = -1
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Снимки"))

        self.list_widget = QListWidget()
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget)

        if self._view_mode:
            legend_text = "[+] есть разметка   — нет разметки"
        else:
            legend_text = "[+] полный   [!] частично   [->] пропущен"

        legend = QLabel(legend_text)
        legend.setStyleSheet("color: gray; font-size: 10px;")
        legend.setWordWrap(True)
        layout.addWidget(legend)

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def set_images(self, image_names):
        self._updating = True
        try:
            self.list_widget.clear()

            self._names = list(image_names)
            self._rows = {name: row for row, name in enumerate(self._names)}
            self._statuses = {name: "none" for name in self._names}
            self._current_row = -1

            for name in self._names:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.list_widget.addItem(item)

            for row in range(len(self._names)):
                self._paint_row(row)
        finally:
            self._updating = False

    def update_status(self, image_name, status):
        row = self._rows.get(image_name)
        if row is None:
            return
        self._statuses[image_name] = status
        self._paint_row(row)

    def set_current_index(self, index):
        if not 0 <= index < len(self._names):
            return

        self._updating = True
        try:
            self._current_row = index
            self.list_widget.setCurrentRow(index)
            item = self.list_widget.item(index)
            if item is not None:
                self.list_widget.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
        finally:
            self._updating = False

    def get_current_index(self):
        return self.list_widget.currentRow()

    def get_image_name(self, index):
        if 0 <= index < len(self._names):
            return self._names[index]
        return None

    # ------------------------------------------------------------------
    # Внутренняя логика
    # ------------------------------------------------------------------

    def _paint_row(self, row):
        item = self.list_widget.item(row)
        if item is None:
            return

        name = self._names[row]
        status = self._statuses.get(name, "none")
        marker = self.STATUS_MARKERS.get(status, "")

        item.setText(f"{marker} {name}".strip())

        if self._view_mode:
            tip = "Есть разметка" if status == "full" else "Нет разметки"
        else:
            tip = f"Статус: {status}"
        item.setToolTip(f"{name}\n{tip}")

        color = self.STATUS_COLORS.get(status)
        if color is not None:
            item.setForeground(QColor(*color))
        else:
            item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def _on_row_changed(self, row):
        if self._updating or row < 0 or row == self._current_row:
            return
        self._current_row = row
        self.image_selected.emit(row)