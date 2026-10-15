from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame,
)

from patch_labeler.config import CLASS_COLORS


class ViewPanel(QWidget):
    """Правая панель режима просмотра. Подсветка по классам."""

    toggle_grid_clicked = Signal()
    prev_image_clicked = Signal()
    next_image_clicked = Signal()
    class_toggled = Signal(str, bool)  # (class_name, is_checked)

    def __init__(self, classes, parent=None):
        super().__init__(parent)
        self.classes = classes

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Заголовок режима
        mode_label = QLabel("Режим: просмотр (только чтение)")
        mode_label.setStyleSheet("font-weight: bold; color: #7cb342;")
        mode_label.setWordWrap(True)
        layout.addWidget(mode_label)

        # Превью
        layout.addWidget(self._section_title("Превью патча"))

        self.preview_image = QLabel()
        self.preview_image.setFixedSize(256, 256)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet(
            "background-color: #2b2b2b; border: 1px solid #555;"
        )
        self.preview_image.setText("Наведите на патч")
        layout.addWidget(self.preview_image, alignment=Qt.AlignmentFlag.AlignCenter)

        self.preview_info = QLabel("—")
        self.preview_info.setWordWrap(True)
        self.preview_info.setStyleSheet("color: #aaa; font-size: 11px;")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_info)

        layout.addWidget(self._separator())

        # Подсветка классов
        layout.addWidget(self._section_title("Подсветка классов"))
        hint = QLabel("Отметьте классы для подсветки:")
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        self.class_checkboxes = {}
        for class_name in classes:
            color = CLASS_COLORS.get(class_name, (200, 200, 200))
            
            # Создаем цветной квадрат 16x16 для иконки
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(*color))
            icon = QIcon(pixmap)

            cb = QCheckBox(f"Класс {class_name}")
            cb.setIcon(icon)
            cb.stateChanged.connect(
                lambda state, cn=class_name: self.class_toggled.emit(
                    cn, state == Qt.CheckState.Checked.value
                )
            )
            self.class_checkboxes[class_name] = cb
            layout.addWidget(cb)

        layout.addWidget(self._separator())

        # Статистика по классам
        layout.addWidget(self._section_title("Статистика"))

        self.class_stats = {}
        for class_name in classes:
            color = CLASS_COLORS.get(class_name, (200, 200, 200))
            color_str = f"rgb({color[0]}, {color[1]}, {color[2]})"

            label = QLabel(
                f'<span style="color: {color_str};">■</span> '
                f'Класс {class_name}: 0'
            )
            label.setTextFormat(Qt.TextFormat.RichText)
            self.class_stats[class_name] = label
            layout.addWidget(label)

        layout.addWidget(self._separator())

        # Сетка
        self.chk_grid_visible = QCheckBox("Скрыть сетку (H)")
        self.chk_grid_visible.setChecked(False)
        self.chk_grid_visible.stateChanged.connect(
            lambda state: self.toggle_grid_clicked.emit()
        )
        layout.addWidget(self.chk_grid_visible)

        layout.addWidget(self._separator())

        # Навигация
        layout.addWidget(self._section_title("Навигация"))

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(6)

        self.btn_prev = QPushButton("← Предыдущий (A)")
        self.btn_prev.clicked.connect(self.prev_image_clicked.emit)
        nav_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Следующий → (D)")
        self.btn_next.clicked.connect(self.next_image_clicked.emit)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def update_preview(self, pixmap, info_text):
        scaled = pixmap.scaled(
            self.preview_image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_image.setPixmap(scaled)
        self.preview_info.setText(info_text)

    def clear_preview(self):
        self.preview_image.clear()
        self.preview_image.setText("Наведите на патч")
        self.preview_info.setText("—")

    def set_grid_visible(self, visible):
        self.chk_grid_visible.blockSignals(True)
        self.chk_grid_visible.setChecked(not visible)
        self.chk_grid_visible.blockSignals(False)

    def update_statistics(self, class_counts):
        for class_name, label in self.class_stats.items():
            count = class_counts.get(class_name, 0)
            color = CLASS_COLORS.get(class_name, (200, 200, 200))
            color_str = f"rgb({color[0]}, {color[1]}, {color[2]})"
            label.setText(
                f'<span style="color: {color_str};">■</span> '
                f'Класс {class_name}: {count}'
            )

    def reset_checkboxes(self):
        """Сбрасывает все чекбоксы (при смене снимка)."""
        for cb in self.class_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    # ------------------------------------------------------------------
    # Помощники
    # ------------------------------------------------------------------

    @staticmethod
    def _section_title(text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold;")
        return label

    @staticmethod
    def _separator():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line