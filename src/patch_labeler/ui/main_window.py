# ui/main_window.py

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStatusBar,
    QFileDialog, QMessageBox, QLabel,
)

from patch_labeler.config import CLASSES, PATCH_SIZE, OVERLAP
from patch_labeler.utils import normalize_for_display, numpy_to_qimage
from patch_labeler.image_processor import ImageProcessor
from patch_labeler.grid_generator import GridGenerator
from patch_labeler.data_manager import DataManager, ViewData
from patch_labeler.patch_manager import PatchManager

from patch_labeler.ui.mode_dialog import choose_mode
from patch_labeler.ui.graphics_view import GraphicsView
from patch_labeler.ui.image_list_panel import ImageListPanel
from patch_labeler.ui.right_panel import RightPanel
from patch_labeler.ui.view_panel import ViewPanel


class MainWindow(QMainWindow):
    SUPPORTED_EXTENSIONS = {".png", ".pgm"}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Patch Labeler")
        self.resize(1600, 900)

        self.ready = False

        self.mode = choose_mode(self)
        if self.mode is None:
            return

        if not self._choose_paths():
            return

        self.image_list = []
        self.current_image_index = -1
        self.current_image_name = None
        self.current_image_16bit = None
        self.patch_manager = None

        if self.mode == "labeling":
            try:
                self.data_manager = DataManager(self.labels_file, self.output_dir)
            except (json.JSONDecodeError, OSError) as e:
                QMessageBox.critical(
                    self, "Ошибка чтения разметки",
                    f"Не удалось загрузить labels.json:\n{e}"
                )
                return
            self.view_data = None
            title = "Patch Labeler — Разметка"
        else:
            try:
                self.view_data = ViewData(self.labels_file)
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка чтения разметки",
                    f"Не удалось загрузить JSON:\n{e}"
                )
                return
            self.data_manager = None
            title = "Patch Labeler — Просмотр разметки"

        self.setWindowTitle(title)

        self.image_processor = ImageProcessor()
        self.grid_generator = GridGenerator()

        self._create_ui()
        self._load_image_list()

        if self.image_list:
            self._restore_or_start_first()
        else:
            QMessageBox.warning(
                self, "Нет снимков",
                f"В папке не найдено файлов PNG/PGM:\n{self.input_dir}"
            )

        self.ready = True

    # ==================================================================
    # Инициализация
    # ==================================================================

    def _choose_paths(self):
        if self.mode == "labeling":
            input_str = QFileDialog.getExistingDirectory(
                self, "Выберите входную папку со снимками"
            )
            if not input_str:
                return False
            self.input_dir = Path(input_str)

            output_str = QFileDialog.getExistingDirectory(
                self, "Выберите выходную папку для патчей и labels.json"
            )
            if not output_str:
                return False
            self.output_dir = Path(output_str)
            self.labels_file = self.output_dir / "labels.json"

        else:
            input_str = QFileDialog.getExistingDirectory(
                self, "Выберите папку со снимками"
            )
            if not input_str:
                return False
            self.input_dir = Path(input_str)
            self.output_dir = None

            json_str, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл разметки (JSON)",
                str(self.input_dir),
                "JSON Files (*.json);;All Files (*)",
            )
            if not json_str:
                return False
            self.labels_file = Path(json_str)

        return True

    def _create_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        self.image_list_panel = ImageListPanel(mode=self.mode)
        self.image_list_panel.image_selected.connect(self._on_image_selected)
        splitter.addWidget(self.image_list_panel)

        self.graphics_view = GraphicsView(editable=(self.mode == "labeling"))
        self.graphics_view.patch_hovered.connect(self._on_patch_hovered)
        if self.mode == "labeling":
            self.graphics_view.patch_clicked.connect(self._on_patch_clicked)
        splitter.addWidget(self.graphics_view)

        if self.mode == "labeling":
            self.right_panel = RightPanel(CLASSES)
            self.right_panel.class_selected.connect(self._on_class_selected)
            self.right_panel.clear_selection_clicked.connect(self._on_clear_selection)
            self.right_panel.clear_labeling_clicked.connect(self._on_clear_labeling)
            self.right_panel.save_clicked.connect(self._on_save)
            self.right_panel.skip_clicked.connect(self._on_skip)
        else:
            self.right_panel = ViewPanel(CLASSES)
            # НОВОЕ: подключение подсветки классов
            self.right_panel.class_toggled.connect(self._on_class_toggled)

        self.right_panel.toggle_grid_clicked.connect(self._on_toggle_grid)
        self.right_panel.prev_image_clicked.connect(self._go_to_prev_image)
        self.right_panel.next_image_clicked.connect(self._go_to_next_image)

        splitter.addWidget(self.right_panel)
        splitter.setSizes([250, 900, 300])

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Файл")
        file_menu.addAction("Выход", self.close)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)

    # ==================================================================
    # Загрузка
    # ==================================================================

    def _load_image_list(self):
        self.image_list = sorted([
            p.name for p in self.input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ])

        self.image_list_panel.set_images(self.image_list)

        for name in self.image_list:
            if self.mode == "labeling":
                status = self.data_manager.get_image_status(name)
            else:
                status = "full" if self.view_data.has_markup(name) else "none"
            self.image_list_panel.update_status(name, status)

    def _restore_or_start_first(self):
        if not self.image_list:
            return

        last_image = None
        if self.data_manager is not None:
            last_image = self.data_manager.get_current_image()

        if last_image and last_image in self.image_list:
            index = self.image_list.index(last_image)
        else:
            index = 0

        self._go_to_image(index)

    def _load_current_image(self):
        if not self.image_list or self.current_image_index < 0:
            return

        self.current_image_name = self.image_list[self.current_image_index]
        image_path = self.input_dir / self.current_image_name

        try:
            self.current_image_16bit = self.image_processor.load_image(str(image_path))
            img_8bit = normalize_for_display(self.current_image_16bit)

            h, w = self.current_image_16bit.shape[:2]
            patches = self.grid_generator.generate_grid(h, w, PATCH_SIZE, OVERLAP)

            source = self.data_manager if self.mode == "labeling" else self.view_data
            self.patch_manager = PatchManager(patches, self.current_image_name, source)

            self.graphics_view.set_image(img_8bit)
            self.graphics_view.set_patches(patches, self.patch_manager)
            self.image_list_panel.set_current_index(self.current_image_index)
            self.right_panel.clear_preview()

            if self.mode == "labeling":
                self.data_manager.set_current_image(self.current_image_name)
                self.data_manager.save_labels()
                self._update_statistics()
            else:
                # НОВОЕ: сброс чекбоксов при смене снимка
                self.right_panel.reset_checkboxes()
                self.graphics_view.set_highlighted_classes(set())
                self._update_view_state()

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить снимок:\n{e}"
            )

    # ==================================================================
    # Навигация
    # ==================================================================

    def _go_to_image(self, index):
        if 0 <= index < len(self.image_list):
            self.current_image_index = index
            self._load_current_image()

    def _go_to_next_image(self):
        if self.current_image_index < len(self.image_list) - 1:
            self._go_to_image(self.current_image_index + 1)
            return

        if self.mode == "view":
            QMessageBox.information(self, "Информация", "Это последний снимок.")
            return

        for i, name in enumerate(self.image_list):
            if self.data_manager.get_image_status(name) == "skipped":
                self._go_to_image(i)
                QMessageBox.information(
                    self, "Информация",
                    "Все снимки обработаны.\nПереход к первому пропущенному."
                )
                return

        QMessageBox.information(self, "Информация", "Все снимки обработаны.")

    def _go_to_prev_image(self):
        if self.current_image_index > 0:
            self._go_to_image(self.current_image_index - 1)

    def _on_image_selected(self, index):
        self._go_to_image(index)

    # ==================================================================
    # Взаимодействие с патчами
    # ==================================================================

    def _on_patch_clicked(self, patch):
        if self.mode != "labeling" or not self.patch_manager:
            return

        self.patch_manager.toggle_patch(patch)
        self.graphics_view.update_patch_state(patch)
        self._update_statistics()

    def _on_patch_hovered(self, patch):
        if patch is None:
            self.right_panel.clear_preview()
            return

        if self.current_image_16bit is None or not self.patch_manager:
            return

        x, y, w, h = patch["coords"]
        patch_16bit = self.current_image_16bit[y:y + h, x:x + w]
        patch_8bit = normalize_for_display(patch_16bit)
        pixmap = QPixmap.fromImage(numpy_to_qimage(patch_8bit))

        class_name = patch["class"] if patch["class"] is not None else "—"

        if self.mode == "labeling":
            info = f"Класс: {class_name} | [{x}, {y}, {w}, {h}] | {patch['state']}"
        else:
            info = f"Класс: {class_name} | [{x}, {y}, {w}, {h}]"

        self.right_panel.update_preview(pixmap, info)

    def _on_class_selected(self, class_name):
        if self.mode != "labeling" or not self.patch_manager:
            return

        if not self.patch_manager.assign_class(class_name):
            QMessageBox.warning(
                self, "Ошибка",
                "Нельзя переназначить класс размеченному патчу.\n"
                "Сначала снимите разметку (Shift+E)."
            )
            return

        for patch in self.patch_manager.patches:
            self.graphics_view.update_patch_state(patch)
        self._update_statistics()

    def _on_clear_selection(self):
        if self.mode != "labeling" or not self.patch_manager:
            return

        self.patch_manager.clear_selection()
        for patch in self.patch_manager.patches:
            self.graphics_view.update_patch_state(patch)
        self._update_statistics()

    def _on_clear_labeling(self):
        if self.mode != "labeling" or not self.patch_manager:
            return

        self.patch_manager.clear_labeling()
        for patch in self.patch_manager.patches:
            self.graphics_view.update_patch_state(patch)
        self._update_statistics()

    # ==================================================================
    # Подсветка классов (режим просмотра)
    # ==================================================================

    def _on_class_toggled(self, class_name, is_checked):
        """Обработка включения/выключения чекбокса класса."""
        if self.mode != "view":
            return

        highlighted = set(self.graphics_view.highlighted_classes)
        if is_checked:
            highlighted.add(class_name)
        else:
            highlighted.discard(class_name)

        self.graphics_view.set_highlighted_classes(highlighted)

    # ==================================================================
    # Сохранение / пропуск
    # ==================================================================

    def _on_save(self):
        if self.mode != "labeling" or not self.patch_manager:
            return

        labeled = self.patch_manager.get_labeled_patches()
        if not labeled:
            QMessageBox.warning(self, "Ошибка", "Нет размеченных патчей для сохранения.")
            return

        self.patch_manager.save_to_json()
        self.data_manager.save_patches(
            self.current_image_name, self.current_image_16bit, labeled
        )

        status = self.data_manager.get_image_status(self.current_image_name)
        self.image_list_panel.update_status(self.current_image_name, status)

        self._go_to_next_image()

    def _on_skip(self):
        if self.mode != "labeling" or not self.patch_manager:
            return

        status = self.data_manager.get_image_status(self.current_image_name)
        if status in ("partly", "full"):
            reply = QMessageBox.question(
                self, "Подтверждение",
                "На снимке есть разметка. Пропустить и удалить разметку?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return
            self.data_manager.delete_old_patches(self.current_image_name)

        self.data_manager.set_image_status(self.current_image_name, "skipped")
        self.data_manager.save_labels()
        self.image_list_panel.update_status(self.current_image_name, "skipped")

        self._go_to_next_image()

    # ==================================================================
    # Сетка
    # ==================================================================

    def _on_toggle_grid(self):
        self.graphics_view.toggle_grid_visibility()
        self.right_panel.set_grid_visible(self.graphics_view.grid_visible)

    # ==================================================================
    # Статистика
    # ==================================================================

    def _update_statistics(self):
        if not self.patch_manager:
            return

        stats = self.patch_manager.get_statistics()
        text = f"Снимок: {stats['labeled']}/{stats['total']}"
        for class_name in CLASSES:
            count = stats["classes"].get(class_name, 0)
            if count:
                text += f" | {class_name}:{count}"

        totals = {}
        for name in self.image_list:
            for class_name in self.data_manager.get_image_patches(name).values():
                if class_name is not None:
                    totals[class_name] = totals.get(class_name, 0) + 1

        text += " | Всего:"
        for class_name in CLASSES:
            count = totals.get(class_name, 0)
            if count:
                text += f" {class_name}:{count}"

        self.status_label.setText(text)

    def _update_view_state(self):
        if not self.patch_manager:
            return

        stats = self.patch_manager.get_statistics()
        self.right_panel.update_statistics(stats["classes"])

        status = "full" if stats["labeled"] > 0 else "none"
        self.image_list_panel.update_status(self.current_image_name, status)

        text = f"Снимок: {stats['labeled']}/{stats['total']} размечено"
        for class_name in CLASSES:
            count = stats["classes"].get(class_name, 0)
            if count:
                text += f" | {class_name}:{count}"

        totals = {}
        for name in self.image_list:
            for class_name in self.view_data.get_image_patches(name).values():
                if class_name is not None:
                    totals[class_name] = totals.get(class_name, 0) + 1

        text += " | Всего:"
        for class_name in CLASSES:
            count = totals.get(class_name, 0)
            if count:
                text += f" {class_name}:{count}"

        self.status_label.setText(text)

    # ==================================================================
    # Горячие клавиши
    # ==================================================================

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if self.mode == "view":
            if key in (Qt.Key.Key_A, Qt.Key.Key_Left):
                self._go_to_prev_image()
            elif key in (Qt.Key.Key_D, Qt.Key.Key_Right):
                self._go_to_next_image()
            elif key == Qt.Key.Key_H:
                self._on_toggle_grid()
            else:
                super().keyPressEvent(event)
            return

        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self._on_skip()
        elif key == Qt.Key.Key_S and modifiers == Qt.KeyboardModifier.NoModifier:
            self._on_save()
        elif key in (Qt.Key.Key_A, Qt.Key.Key_Left):
            self._go_to_prev_image()
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Right):
            self._go_to_next_image()
        elif key == Qt.Key.Key_E and modifiers == Qt.KeyboardModifier.NoModifier:
            self._on_clear_selection()
        elif key == Qt.Key.Key_E and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self._on_clear_labeling()
        elif key == Qt.Key.Key_H:
            self._on_toggle_grid()
        elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            index = key - Qt.Key.Key_1
            if index < len(CLASSES):
                self._on_class_selected(CLASSES[index])
        else:
            super().keyPressEvent(event)