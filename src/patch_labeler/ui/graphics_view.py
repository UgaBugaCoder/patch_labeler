from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
)

from patch_labeler.config import STATE_COLORS, CLASS_COLORS, GRID_COLOR, GRID_WIDTH, FRAME_WIDTH, HOVER_WIDTH
from patch_labeler.utils import numpy_to_qimage


class PatchItem(QGraphicsRectItem):
    def __init__(self, patch):
        super().__init__()
        self.patch = patch
        self.hover_enter_callback = None
        self.hover_leave_callback = None

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    def hoverEnterEvent(self, event):
        if self.hover_enter_callback is not None:
            self.hover_enter_callback(self.patch)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self.hover_leave_callback is not None:
            self.hover_leave_callback(self.patch)
        super().hoverLeaveEvent(event)


class GraphicsView(QGraphicsView):
    patch_clicked = Signal(object)
    patch_hovered = Signal(object)

    def __init__(self, parent=None, editable=True):
        super().__init__(parent)

        self.editable = editable
        self.highlighted_classes = set()  # НОВОЕ: множество подсвечиваемых классов

        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.image_item = None
        self.patch_items = {}
        self.state_items = {}

        self.patches = []
        self.patch_manager = None
        self.grid_visible = True

        # Hover-рамка
        self.hover_item = QGraphicsRectItem()
        self.hover_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.hover_item.setPen(QPen(QColor(255, 255, 255), HOVER_WIDTH))
        self.hover_item.setZValue(1000)
        self.hover_item.setVisible(False)
        self.hover_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.hover_item.setAcceptHoverEvents(False)
        self.scene().addItem(self.hover_item)

        # ЛКМ
        self._press_pos = None
        self._press_patch = None
        self._brush_mode = "select"
        self._is_stroke = False
        self._processed = set()

        # ПКМ
        self._is_panning = False
        self._last_pan_pos = None

    # ------------------------------------------------------------------
    # Изображение и сетка
    # ------------------------------------------------------------------

    def set_image(self, img_8bit):
        qimage = numpy_to_qimage(img_8bit)
        pixmap = QPixmap.fromImage(qimage)

        if self.image_item is not None:
            self.scene().removeItem(self.image_item)

        self.image_item = QGraphicsPixmapItem(pixmap)
        self.image_item.setZValue(0)
        self.scene().addItem(self.image_item)

        self.setSceneRect(self.image_item.boundingRect())
        self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.hover_item.setVisible(False)

    def set_patches(self, patches, patch_manager):
        self._reset_stroke()
        self.hover_item.setVisible(False)

        for item in self.patch_items.values():
            self.scene().removeItem(item)
        for item in self.state_items.values():
            self.scene().removeItem(item)
        self.patch_items.clear()
        self.state_items.clear()

        self.patches = patches
        self.patch_manager = patch_manager

        for patch in patches:
            x, y, w, h = patch["coords"]
            rect = QRectF(x, y, w, h)

            pi = PatchItem(patch)
            pi.setRect(rect)
            pi.setZValue(1)
            pi.hover_enter_callback = self._on_hover_enter
            pi.hover_leave_callback = self._on_hover_leave
            self.scene().addItem(pi)
            self.patch_items[patch["index"]] = pi

            si = QGraphicsRectItem(rect)
            si.setZValue(2)
            si.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            si.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            si.setAcceptHoverEvents(False)
            self.scene().addItem(si)
            self.state_items[patch["index"]] = si

            self._update_patch_visuals(patch)

    # ------------------------------------------------------------------
    # Подсветка классов (режим просмотра)
    # ------------------------------------------------------------------

    def set_highlighted_classes(self, class_names):
        """Устанавливает множество классов для подсветки."""
        self.highlighted_classes = set(class_names)
        # Обновляем все патчи
        for patch in self.patches:
            self._update_patch_visuals(patch)

    # ------------------------------------------------------------------
    # Визуализация
    # ------------------------------------------------------------------

    def _update_patch_visuals(self, patch):
        idx = patch["index"]
        state = patch["state"]
        pi = self.patch_items[idx]
        si = self.state_items[idx]

        # Тонкая сетка
        if self.grid_visible:
            pi.setPen(QPen(QColor(*GRID_COLOR), GRID_WIDTH))
        else:
            pi.setPen(QPen(Qt.PenStyle.NoPen))
        pi.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        if not self.editable:
            # РЕЖИМ ПРОСМОТРА: подсветка по классам
            class_name = patch.get("class")
            if state == "labeled" and class_name in self.highlighted_classes:
                color = CLASS_COLORS.get(class_name, (255, 255, 255))
                si.setPen(QPen(QColor(*color), FRAME_WIDTH))
                si.setVisible(True)
            else:
                si.setVisible(False)
        else:
            # РЕЖИМ РАЗМЕТКИ: рамка по STATE_COLORS
            if state in ("selected", "labeled"):
                si.setPen(QPen(QColor(*STATE_COLORS[state]), FRAME_WIDTH))
                si.setVisible(True)
            else:
                si.setVisible(False)

    def update_patch_state(self, patch):
        self._update_patch_visuals(patch)

    def toggle_grid_visibility(self):
        self.grid_visible = not self.grid_visible
        for patch in self.patches:
            self._update_patch_visuals(patch)

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    def _on_hover_enter(self, patch):
        x, y, w, h = patch["coords"]
        self.hover_item.setRect(QRectF(x, y, w, h))
        self.hover_item.setVisible(True)
        self.patch_hovered.emit(patch)

    def _on_hover_leave(self, patch):
        self.hover_item.setVisible(False)
        self.patch_hovered.emit(None)

    # ------------------------------------------------------------------
    # Hit-test
    # ------------------------------------------------------------------

    def _get_patch_at(self, scene_pos):
        items = self.scene().items(
            scene_pos,
            Qt.ItemSelectionMode.IntersectsItemShape,
            Qt.SortOrder.DescendingOrder,
            self.transform(),
        )
        for item in items:
            if isinstance(item, PatchItem):
                return item.patch
        return None

    # ------------------------------------------------------------------
    # Мышь
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if not self.editable:
                event.accept()
                return

            self._press_pos = event.pos()
            self._is_stroke = False
            self._processed = set()
            self._brush_mode = "select"

            self._press_patch = self._get_patch_at(self.mapToScene(event.pos()))

            if self._press_patch is not None:
                state = self._press_patch["state"]
                self._brush_mode = "select" if state == "unlabeled" else "deselect"

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        if self._press_pos is not None and self.editable:
            if not self._is_stroke:
                delta = event.pos() - self._press_pos
                if delta.manhattanLength() > 5:
                    self._is_stroke = True
                    self._apply_brush(self._press_patch)

            if self._is_stroke:
                patch = self._get_patch_at(self.mapToScene(event.pos()))
                self._apply_brush(patch)

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = False
            self._last_pan_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if (self.editable
                    and self._press_pos is not None
                    and not self._is_stroke
                    and self._press_patch is not None):
                self.patch_clicked.emit(self._press_patch)

            self._reset_stroke()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _reset_stroke(self):
        self._press_pos = None
        self._press_patch = None
        self._is_stroke = False
        self._processed = set()

    def _apply_brush(self, patch):
        if patch is None or not self.editable:
            return

        idx = patch["index"]
        if idx in self._processed:
            return
        self._processed.add(idx)

        state = patch["state"]

        if self._brush_mode == "select":
            if state == "unlabeled":
                self.patch_manager.select_patch(patch)
                self.update_patch_state(patch)
        else:
            if state == "labeled":
                self.patch_manager.toggle_patch(patch)
                self.update_patch_state(patch)
            elif state == "selected":
                self.patch_manager.deselect_patch(patch)
                self.update_patch_state(patch)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.scale(factor, factor)
        event.accept()