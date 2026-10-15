# ui/right_panel.py

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QSizePolicy
)


class RightPanel(QWidget):
    """Правая панель: превью патча, классы, кнопки управления."""

    # Сигналы
    class_selected = Signal(str)          # Выбран класс (передает имя класса)
    clear_selection_clicked = Signal()    # Кнопка "Снять выделение"
    clear_labeling_clicked = Signal()     # Кнопка "Снять разметку"
    save_clicked = Signal()               # Кнопка "Нарезать и сохранить"
    skip_clicked = Signal()               # Кнопка "Пропустить"
    toggle_grid_clicked = Signal()        # Кнопка "Скрыть/показать сетку"
    prev_image_clicked = Signal()         # Кнопка "Предыдущий"
    next_image_clicked = Signal()         # Кнопка "Следующий"

    def __init__(self, classes, parent=None):
        """
        Args:
            classes: Список имен классов (например, ["1", "2", "3", "4"]).
        """
        super().__init__(parent)
        self.classes = classes

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # ============================================================
        # Блок 1: Превью патча
        # ============================================================
        preview_label = QLabel("Превью патча")
        preview_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(preview_label)

        # Изображение патча
        self.preview_image = QLabel()
        self.preview_image.setFixedSize(256, 256)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet(
            "background-color: #2b2b2b; border: 1px solid #555;"
        )
        self.preview_image.setText("Наведите на патч")
        self.preview_image.setScaledContents(False)
        layout.addWidget(self.preview_image, alignment=Qt.AlignmentFlag.AlignCenter)

        # Информация о патче
        self.preview_info = QLabel("—")
        self.preview_info.setWordWrap(True)
        self.preview_info.setStyleSheet("color: #aaa; font-size: 11px;")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_info)

        # Разделитель
        layout.addWidget(self._create_separator())

        # ============================================================
        # Блок 2: Классы
        # ============================================================
        classes_label = QLabel("Классы")
        classes_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(classes_label)

        # Кнопки классов (2 колонки)
        classes_grid = QHBoxLayout()
        classes_grid.setSpacing(6)

        self.class_buttons = {}
        for i, class_name in enumerate(classes):
            btn = QPushButton(f"{i + 1}: {class_name}")
            btn.setCheckable(False)
            btn.setToolTip(f"Горячая клавиша: {i + 1}")
            btn.clicked.connect(lambda checked, c=class_name: self.class_selected.emit(c))
            self.class_buttons[class_name] = btn

            # Добавляем в сетку (2 колонки)
            if i % 2 == 0:
                row_layout = QHBoxLayout()
                row_layout.setSpacing(6)
                classes_grid.addLayout(row_layout)
            row_layout.addWidget(btn)

        layout.addLayout(classes_grid)

        # Разделитель
        layout.addWidget(self._create_separator())

        # ============================================================
        # Блок 3: Управление
        # ============================================================
        control_label = QLabel("Управление")
        control_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(control_label)

        self.btn_clear_selection = QPushButton("Снять выделение (E)")
        self.btn_clear_selection.clicked.connect(self.clear_selection_clicked.emit)
        layout.addWidget(self.btn_clear_selection)

        self.btn_clear_labeling = QPushButton("Снять разметку (Shift+E)")
        self.btn_clear_labeling.clicked.connect(self.clear_labeling_clicked.emit)
        layout.addWidget(self.btn_clear_labeling)

        # Разделитель
        layout.addWidget(self._create_separator())

        self.btn_save = QPushButton("Нарезать и сохранить (S)")
        self.btn_save.setStyleSheet("font-weight: bold;")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(self.btn_save)

        self.btn_skip = QPushButton("Пропустить (Ctrl+S)")
        self.btn_skip.clicked.connect(self.skip_clicked.emit)
        layout.addWidget(self.btn_skip)

        # Разделитель
        layout.addWidget(self._create_separator())

        # Чекбокс для скрытия сетки
        self.chk_grid_visible = QCheckBox("Скрыть сетку (H)")
        self.chk_grid_visible.setChecked(False)  # По умолчанию сетка показана
        self.chk_grid_visible.stateChanged.connect(
            lambda state: self.toggle_grid_clicked.emit()
        )
        layout.addWidget(self.chk_grid_visible)

        # Разделитель
        layout.addWidget(self._create_separator())

        # ============================================================
        # Блок 4: Навигация
        # ============================================================
        nav_label = QLabel("Навигация")
        nav_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(nav_label)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(6)

        self.btn_prev = QPushButton("← Предыдущий (A)")
        self.btn_prev.clicked.connect(self.prev_image_clicked.emit)
        nav_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Следующий → (D)")
        self.btn_next.clicked.connect(self.next_image_clicked.emit)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)

        # Растягиваем нижнюю часть
        layout.addStretch()

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def update_preview(self, pixmap, info_text):
        """
        Обновляет превью патча.

        Args:
            pixmap: QPixmap (8-битное изображение патча).
            info_text: Строка с информацией (класс, координаты, состояние).
        """
        # Масштабируем pixmap до размера QLabel с сохранением пропорций
        scaled_pixmap = pixmap.scaled(
            self.preview_image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_image.setPixmap(scaled_pixmap)
        self.preview_info.setText(info_text)

    def clear_preview(self):
        """Очищает превью (когда курсор не на патче)."""
        self.preview_image.clear()
        self.preview_image.setText("Наведите на патч")
        self.preview_info.setText("—")

    def set_grid_visible(self, visible):
        """
        Устанавливает состояние чекбокса "Скрыть сетку".
        Вызывается из MainWindow при программном переключении (например, горячей клавишей).
        """
        # Блокируем сигнал, чтобы не вызвать рекурсию
        self.chk_grid_visible.blockSignals(True)
        self.chk_grid_visible.setChecked(not visible)  # Инвертируем: если сетка видна → чекбокс не отмечен
        self.chk_grid_visible.blockSignals(False)

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _create_separator(self):
        """Создает горизонтальный разделитель."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line