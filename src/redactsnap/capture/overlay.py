"""
Interactive Snipping Overlay for RedactSnap v0.5.0.
Combines:
- Frameless multi-monitor virtual desktop capture
- Real-time 8x pixel magnifier loupe
- Glassmorphism action toolbar
- Smart vector annotations (Step numbers, arrows, boxes, highlighters, spotlights)
- Screen recording with timer HUD
- Instant zero-server link sharing (Imgur / S3)
- Live redaction & studio beautifier
"""

from enum import Enum, auto
from typing import Optional, Tuple, List

from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QFont,
    QFontMetrics,
    QCursor,
    QImage,
    QPainterPath,
)

from .grabber import ScreenGrabber
from .recorder import ScreenRecorder
from ..ui.toolbar import FloatingToolbar
from ..ui.hud import ToastHUD
from ..studio.annotations import Annotation, AnnotationType, AnnotationRenderer
from ..studio.beautifier import StudioBeautifier, StudioConfig
from ..studio.presets import PRESETS, get_preset_by_id
from ..redaction.engine import RedactionPipeline
from ..redaction.masker import RedactionStyle
from ..core.uploader import UploadWorker, UploadProvider, UploadResult
from ..core.config import ConfigManager


class OverlayState(Enum):
    READY = auto()
    DRAGGING = auto()
    SELECTED = auto()
    ANNOTATING = auto()
    MOVING = auto()
    RESIZING = auto()


class ResizeHandle(Enum):
    NONE = auto()
    TOP_LEFT = auto()
    TOP_MID = auto()
    TOP_RIGHT = auto()
    MID_RIGHT = auto()
    BOTTOM_RIGHT = auto()
    BOTTOM_MID = auto()
    BOTTOM_LEFT = auto()
    MID_LEFT = auto()


class SnippingOverlay(QWidget):
    """
    Transparent fullscreen overlay capturing mouse drag events across all monitors.
    """

    confirmed = pyqtSignal(QPixmap, QRect)
    cancelled = pyqtSignal()

    HANDLE_SIZE = 8
    LOUPE_RADIUS = 60
    LOUPE_GRID_SIZE = 15
    LOUPE_ZOOM = 8

    def __init__(self, virtual_pixmap: QPixmap, virtual_rect: QRect, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.virtual_pixmap = virtual_pixmap
        self.virtual_rect = virtual_rect

        self.state = OverlayState.READY
        self.active_handle = ResizeHandle.NONE

        self.origin_point = QPoint()
        self.current_point = QPoint()
        self.selection_rect = QRect()
        self.move_offset = QPoint()

        # Cached image for loupe
        self._cached_qimage = self.virtual_pixmap.toImage()

        # Live transformation state
        self._is_redacted = False
        self._current_preset_idx = -1
        self._redaction_pipeline: Optional[RedactionPipeline] = None
        self._cached_processed_pixmap: Optional[QPixmap] = None

        # Annotations state
        self.annotations: List[Annotation] = []
        self.active_anno_tool: Optional[AnnotationType] = None
        self._anno_start_pos: Optional[QPoint] = None
        self._step_counter = 1

        # Recording state
        self.recorder = ScreenRecorder(self)
        self.recorder.tick.connect(self._on_recorder_tick)
        self.recorder.finished.connect(self._on_recorder_finished)
        self.recorder.failed.connect(self._on_recorder_failed)

        self._upload_worker: Optional[UploadWorker] = None

        self._init_window()
        self._init_ui_components()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setGeometry(self.virtual_rect)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _init_ui_components(self):
        self.toolbar = FloatingToolbar(self)
        self.toast = ToastHUD(self)

        self.toolbar.copy_clicked.connect(self._confirm_to_clipboard)
        self.toolbar.redact_toggled.connect(self._on_redact_toggled)
        self.toolbar.beautify_cycle.connect(self._on_beautify_cycle)
        self.toolbar.ocr_clicked.connect(self._on_ocr_clicked)
        self.toolbar.save_clicked.connect(self._on_save_clicked)
        self.toolbar.upload_clicked.connect(self._on_upload_clicked)
        self.toolbar.record_toggle.connect(self._on_record_toggled)
        self.toolbar.annotation_selected.connect(self._on_annotation_tool_selected)
        self.toolbar.undo_annotation.connect(self._undo_last_annotation)
        self.toolbar.cancel_clicked.connect(self._cancel)

    # --------------------------------------------------------------------------
    # Mouse Events
    # --------------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            if event.button() == Qt.MouseButton.RightButton:
                if self.state in (OverlayState.SELECTED, OverlayState.ANNOTATING):
                    self._reset_selection()
                else:
                    self._cancel()
            return

        pos = event.pos()

        # If annotation tool active and clicked inside selection
        if self.active_anno_tool is not None and self.selection_rect.contains(pos):
            self.state = OverlayState.ANNOTATING
            rel_x = pos.x() - self.selection_rect.x()
            rel_y = pos.y() - self.selection_rect.y()
            self._anno_start_pos = pos

            if self.active_anno_tool == AnnotationType.STEP_NUMBER:
                # Instant drop of step number
                anno = Annotation(
                    type=AnnotationType.STEP_NUMBER,
                    start_pos=(rel_x, rel_y),
                    end_pos=(rel_x, rel_y),
                    text=str(self._step_counter)
                )
                self.annotations.append(anno)
                self._step_counter += 1
                self.state = OverlayState.SELECTED
                self.update()
            return

        if self.state in (OverlayState.SELECTED, OverlayState.ANNOTATING):
            handle = self._hit_test_handle(pos)
            if handle != ResizeHandle.NONE:
                self.state = OverlayState.RESIZING
                self.active_handle = handle
                self.origin_point = pos
                self.toolbar.hide()
                return

            if self.selection_rect.contains(pos):
                self.state = OverlayState.MOVING
                self.move_offset = pos - self.selection_rect.topLeft()
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.toolbar.hide()
                return

        # Start fresh selection
        self.state = OverlayState.DRAGGING
        self.origin_point = pos
        self.current_point = pos
        self.selection_rect = QRect(pos, QSize(0, 0))
        self.annotations.clear()
        self._step_counter = 1
        self._cached_processed_pixmap = None
        self.toolbar.hide()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.current_point = pos

        if self.state == OverlayState.ANNOTATING:
            self.update()

        elif self.state == OverlayState.DRAGGING:
            self.selection_rect = QRect(self.origin_point, pos).normalized()
            self.update()

        elif self.state == OverlayState.MOVING:
            new_top_left = pos - self.move_offset
            new_top_left.setX(max(0, min(new_top_left.x(), self.width() - self.selection_rect.width())))
            new_top_left.setY(max(0, min(new_top_left.y(), self.height() - self.selection_rect.height())))
            self.selection_rect.moveTo(new_top_left)
            self.update()

        elif self.state == OverlayState.RESIZING:
            self._resize_selection(pos)
            self.update()

        elif self.state == OverlayState.SELECTED:
            handle = self._hit_test_handle(pos)
            if handle in (ResizeHandle.TOP_LEFT, ResizeHandle.BOTTOM_RIGHT):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in (ResizeHandle.TOP_RIGHT, ResizeHandle.BOTTOM_LEFT):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in (ResizeHandle.TOP_MID, ResizeHandle.BOTTOM_MID):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif handle in (ResizeHandle.MID_LEFT, ResizeHandle.MID_RIGHT):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif self.active_anno_tool is not None:
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self.selection_rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            self.update()

        else:
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.state == OverlayState.ANNOTATING and self._anno_start_pos is not None:
                pos = event.pos()
                sx = self._anno_start_pos.x() - self.selection_rect.x()
                sy = self._anno_start_pos.y() - self.selection_rect.y()
                ex = pos.x() - self.selection_rect.x()
                ey = pos.y() - self.selection_rect.y()

                if abs(ex - sx) > 3 or abs(ey - sy) > 3:
                    anno = Annotation(
                        type=self.active_anno_tool,
                        start_pos=(sx, sy),
                        end_pos=(ex, ey)
                    )
                    self.annotations.append(anno)

                self._anno_start_pos = None
                self.state = OverlayState.SELECTED
                self.update()
                return

            if self.state in (OverlayState.DRAGGING, OverlayState.MOVING, OverlayState.RESIZING):
                if self.selection_rect.width() >= 12 and self.selection_rect.height() >= 12:
                    self.state = OverlayState.SELECTED
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.toolbar.anchor_to_selection(self.selection_rect, self.rect())
                else:
                    self._reset_selection()
                self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.state == OverlayState.SELECTED and self.selection_rect.contains(event.pos()):
                self._confirm_to_clipboard()

    # --------------------------------------------------------------------------
    # Keyboard Events
    # --------------------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Escape:
            self._cancel()
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
                self._confirm_to_clipboard()
            return

        if key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ControlModifier):
            if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
                self._confirm_to_clipboard()
            return

        if key == Qt.Key.Key_Z and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self._undo_last_annotation()
            return

        if key == Qt.Key.Key_S and (modifiers & Qt.KeyboardModifier.ControlModifier):
            if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
                self._on_save_clicked()
            return

        if self.state in (OverlayState.SELECTED, OverlayState.ANNOTATING):
            step = 10 if (modifiers & Qt.KeyboardModifier.ShiftModifier) else 1
            if key == Qt.Key.Key_Left:
                self.selection_rect.translate(-step, 0)
            elif key == Qt.Key.Key_Right:
                self.selection_rect.translate(step, 0)
            elif key == Qt.Key.Key_Up:
                self.selection_rect.translate(0, -step)
            elif key == Qt.Key.Key_Down:
                self.selection_rect.translate(0, step)
            self.toolbar.anchor_to_selection(self.selection_rect, self.rect())
            self.update()

    # --------------------------------------------------------------------------
    # Handlers & Actions
    # --------------------------------------------------------------------------

    def _get_current_image(self) -> QPixmap:
        """Composites cropped selection with redactions, annotations, and beautifier."""
        cropped = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
        pil_img = ScreenGrabber.pixmap_to_pil(cropped)

        # 1. Redaction
        if self._is_redacted:
            if self._redaction_pipeline is None:
                self._redaction_pipeline = RedactionPipeline()
            pil_img, _ = self._redaction_pipeline.process(pil_img, style=RedactionStyle.GAUSSIAN_BLUR)

        # 2. Annotations
        if self.annotations:
            pil_img = AnnotationRenderer.render_on_image(pil_img, self.annotations)

        # 3. Studio Beautification
        if self._current_preset_idx >= 0:
            preset = PRESETS[self._current_preset_idx]
            config = StudioConfig(preset=preset, padding=40, show_window_chrome=True, corner_radius=12)
            pil_img = StudioBeautifier.render(pil_img, config)

        return ScreenGrabber.pil_to_pixmap(pil_img)

    def _on_redact_toggled(self, active: bool):
        self._is_redacted = active
        self._cached_processed_pixmap = None

        if active:
            if self._redaction_pipeline is None:
                self._redaction_pipeline = RedactionPipeline()
            cropped = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
            pil_img = ScreenGrabber.pixmap_to_pil(cropped)
            targets, _ = self._redaction_pipeline.detector.scan(pil_img)
            count = len(targets)
            self.toolbar.set_redact_active(True, count=count)
            msg = f"🛡️ Auto-redacted {count} secret(s)!" if count > 0 else "ℹ️ No sensitive secrets detected"
            self.toast.show_message(msg, 2000)
        else:
            self.toolbar.set_redact_active(False)
            self.toast.show_message("🛡️ Redaction removed", 1500)

        self.update()

    def _on_beautify_cycle(self):
        self._current_preset_idx += 1
        if self._current_preset_idx >= len(PRESETS):
            self._current_preset_idx = -1

        self._cached_processed_pixmap = None

        if self._current_preset_idx == -1:
            self.toolbar.set_beautify_preset("Off")
            self.toast.show_message("🎨 Frame: Off", 1500)
        else:
            preset = PRESETS[self._current_preset_idx]
            self.toolbar.set_beautify_preset(preset.name)
            self.toast.show_message(f"🎨 Frame: {preset.name}", 1500)

        self.update()

    def _on_annotation_tool_selected(self, tool: Optional[AnnotationType]):
        self.active_anno_tool = tool
        if tool is not None:
            self.toast.show_message(f"✏️ Tool: {tool.value.capitalize()}", 1200)

    def _undo_last_annotation(self):
        if self.annotations:
            removed = self.annotations.pop()
            if removed.type == AnnotationType.STEP_NUMBER and self._step_counter > 1:
                self._step_counter -= 1
            self.toast.show_message("↩️ Undone", 1000)
            self.update()

    def _on_ocr_clicked(self):
        if self._redaction_pipeline is None:
            self._redaction_pipeline = RedactionPipeline()

        cropped = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
        pil_img = ScreenGrabber.pixmap_to_pil(cropped)

        text = self._redaction_pipeline.copy_as_text(pil_img, redact_secrets=self._is_redacted)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

        self.toast.show_message(f"✓ Copied {len(text)} characters to clipboard!", 2200)

    def _on_record_toggled(self, is_recording: bool):
        if is_recording:
            self.recorder.start(
                target_rect=self.selection_rect,
                fps=30,
                output_format="gif",
                auto_redact=self._is_redacted
            )
            self.toast.show_message("⏺ Recording started...", 1500)
        else:
            self.recorder.stop()
            self.toast.show_message("⏳ Encoding recording...", 3000)

    def _on_recorder_tick(self, seconds: int):
        self.toolbar.update_record_timer(seconds)

    def _on_recorder_finished(self, file_path: str, fmt: str):
        self.toast.show_message(f"✓ Saved {fmt.upper()} to {file_path}", 2500)

    def _on_recorder_failed(self, err: str):
        self.toast.show_message(f"❌ Recording error: {err}", 3000)

    def _on_upload_clicked(self):
        """Asynchronously uploads image to Imgur or S3."""
        pixmap = self._get_current_image()
        pil_img = ScreenGrabber.pixmap_to_pil(pixmap)

        self.toast.show_message("🚀 Uploading to Imgur...", 4000)

        self._upload_worker = UploadWorker(pil_img, provider=UploadProvider.IMGUR)
        self._upload_worker.upload_finished.connect(self._on_upload_finished)
        self._upload_worker.start()

    def _on_upload_finished(self, result: UploadResult):
        if result.success:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(result.url)
            self.toast.show_message(f"✓ Link copied: {result.url}", 4000)
        else:
            self.toast.show_message(f"❌ Upload failed: {result.error_message}", 3500)

    def _on_save_clicked(self):
        pixmap = self._get_current_image()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            "screenshot.png",
            "PNG Image (*.png);;JPEG Image (*.jpg);;WebP Image (*.webp)"
        )
        if file_path:
            pixmap.save(file_path)
            self.toast.show_message(f"✓ Saved to {file_path}", 2000)
            self.confirmed.emit(pixmap, self.selection_rect)
            self.close()

    # --------------------------------------------------------------------------
    # Paint Pipeline
    # --------------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Base frozen snapshot
        painter.drawPixmap(0, 0, self.virtual_pixmap)

        # 2. Dim shroud
        dim_color = QColor(0, 0, 0, 110)
        painter.fillRect(self.rect(), dim_color)

        has_selection = self.selection_rect.isValid() and not self.selection_rect.isEmpty()

        # 3. Selection cutout and preview
        if has_selection:
            # Draw preview
            painter.drawPixmap(self.selection_rect, self.virtual_pixmap, self.selection_rect)

            # Draw live annotations
            if self.annotations:
                AnnotationRenderer.render_with_qpainter(
                    painter,
                    self.annotations,
                    origin_offset=(self.selection_rect.x(), self.selection_rect.y())
                )

            # Draw active in-progress annotation preview
            if self.state == OverlayState.ANNOTATING and self._anno_start_pos is not None:
                p1 = self._anno_start_pos
                p2 = self.current_point
                painter.setPen(QPen(QColor(255, 59, 48), 2, Qt.PenStyle.DashLine))
                painter.drawLine(p1, p2)

            # Outer border
            pen_blue = QPen(QColor(10, 132, 255), 2)
            painter.setPen(pen_blue)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.selection_rect)

            pen_inner = QPen(QColor(255, 255, 255, 140), 1)
            painter.setPen(pen_inner)
            painter.drawRect(self.selection_rect.adjusted(1, 1, -1, -1))

            if self.state in (OverlayState.SELECTED, OverlayState.RESIZING, OverlayState.MOVING):
                self._draw_handles(painter)

            self._draw_dimension_badge(painter)

        # 4. Magnifier loupe
        if self.state in (OverlayState.READY, OverlayState.DRAGGING):
            self._draw_loupe(painter, self.current_point)

        painter.end()

    # --------------------------------------------------------------------------
    # Sub-renderers
    # --------------------------------------------------------------------------

    def _draw_handles(self, painter: QPainter):
        painter.setPen(QPen(QColor(10, 132, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for rect in self._get_handle_rects().values():
            painter.drawRoundedRect(rect, 2, 2)

    def _get_handle_rects(self) -> dict[ResizeHandle, QRect]:
        r = self.selection_rect
        s = self.HANDLE_SIZE
        half_s = s // 2
        cx = r.left() + r.width() // 2
        cy = r.top() + r.height() // 2

        return {
            ResizeHandle.TOP_LEFT: QRect(r.left() - half_s, r.top() - half_s, s, s),
            ResizeHandle.TOP_MID: QRect(cx - half_s, r.top() - half_s, s, s),
            ResizeHandle.TOP_RIGHT: QRect(r.right() - half_s, r.top() - half_s, s, s),
            ResizeHandle.MID_RIGHT: QRect(r.right() - half_s, cy - half_s, s, s),
            ResizeHandle.BOTTOM_RIGHT: QRect(r.right() - half_s, r.bottom() - half_s, s, s),
            ResizeHandle.BOTTOM_MID: QRect(cx - half_s, r.bottom() - half_s, s, s),
            ResizeHandle.BOTTOM_LEFT: QRect(r.left() - half_s, r.bottom() - half_s, s, s),
            ResizeHandle.MID_LEFT: QRect(r.left() - half_s, cy - half_s, s, s),
        }

    def _hit_test_handle(self, pos: QPoint) -> ResizeHandle:
        for handle, rect in self._get_handle_rects().items():
            expanded = rect.adjusted(-3, -3, 3, 3)
            if expanded.contains(pos):
                return handle
        return ResizeHandle.NONE

    def _resize_selection(self, pos: QPoint):
        r = self.selection_rect
        h = self.active_handle

        if h == ResizeHandle.TOP_LEFT:
            self.selection_rect = QRect(pos, r.bottomRight()).normalized()
        elif h == ResizeHandle.TOP_MID:
            self.selection_rect = QRect(QPoint(r.left(), pos.y()), r.bottomRight()).normalized()
        elif h == ResizeHandle.TOP_RIGHT:
            self.selection_rect = QRect(QPoint(r.left(), pos.y()), QPoint(pos.x(), r.bottom())).normalized()
        elif h == ResizeHandle.MID_RIGHT:
            self.selection_rect = QRect(r.topLeft(), QPoint(pos.x(), r.bottom())).normalized()
        elif h == ResizeHandle.BOTTOM_RIGHT:
            self.selection_rect = QRect(r.topLeft(), pos).normalized()
        elif h == ResizeHandle.BOTTOM_MID:
            self.selection_rect = QRect(r.topLeft(), QPoint(r.right(), pos.y())).normalized()
        elif h == ResizeHandle.BOTTOM_LEFT:
            self.selection_rect = QRect(QPoint(pos.x(), r.top()), QPoint(r.right(), pos.y())).normalized()
        elif h == ResizeHandle.MID_LEFT:
            self.selection_rect = QRect(QPoint(pos.x(), r.top()), r.bottomRight()).normalized()

    def _draw_dimension_badge(self, painter: QPainter):
        w, h = self.selection_rect.width(), self.selection_rect.height()
        text = f"{w} × {h} px"

        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        padding_x, padding_y = 10, 5
        badge_w = text_width + padding_x * 2
        badge_h = text_height + padding_y * 2

        badge_x = self.selection_rect.center().x() - badge_w // 2
        badge_y = self.selection_rect.bottom() + 10
        if badge_y + badge_h > self.height() - 10:
            badge_y = self.selection_rect.top() - badge_h - 10

        badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)

        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
        painter.drawRoundedRect(badge_rect, 6, 6)

        painter.setPen(QColor(241, 245, 249))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_loupe(self, painter: QPainter, center_pos: QPoint):
        offset_x, offset_y = 25, 25
        loupe_diameter = self.LOUPE_RADIUS * 2
        extra_h = 28
        total_h = loupe_diameter + extra_h

        lx = center_pos.x() + offset_x
        ly = center_pos.y() + offset_y

        if lx + loupe_diameter > self.width() - 20:
            lx = center_pos.x() - loupe_diameter - offset_x
        if ly + total_h > self.height() - 20:
            ly = center_pos.y() - total_h - offset_y

        px = max(0, min(center_pos.x(), self._cached_qimage.width() - 1))
        py = max(0, min(center_pos.y(), self._cached_qimage.height() - 1))
        pixel_color = self._cached_qimage.pixelColor(px, py)
        hex_color = pixel_color.name().upper()

        half_grid = self.LOUPE_GRID_SIZE // 2
        sample_rect = QRect(px - half_grid, py - half_grid, self.LOUPE_GRID_SIZE, self.LOUPE_GRID_SIZE)
        sample_qimg = self._cached_qimage.copy(sample_rect)

        scaled_pixmap = QPixmap.fromImage(
            sample_qimg.scaled(
                loupe_diameter,
                loupe_diameter,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
        )

        painter.save()
        container_rect = QRect(lx, ly, loupe_diameter, total_h)
        container_path = QPainterPath()
        container_path.addRoundedRect(
            float(container_rect.x()),
            float(container_rect.y()),
            float(container_rect.width()),
            float(container_rect.height()),
            12.0,
            12.0
        )

        painter.setClipPath(container_path)
        painter.fillPath(container_path, QBrush(QColor(15, 23, 42, 240)))

        view_rect = QRect(lx, ly, loupe_diameter, loupe_diameter)
        painter.drawPixmap(view_rect, scaled_pixmap)

        cell_size = loupe_diameter / self.LOUPE_GRID_SIZE
        grid_pen = QPen(QColor(255, 255, 255, 35), 1)
        painter.setPen(grid_pen)
        for i in range(1, self.LOUPE_GRID_SIZE):
            x_line = int(lx + i * cell_size)
            y_line = int(ly + i * cell_size)
            painter.drawLine(x_line, ly, x_line, ly + loupe_diameter)
            painter.drawLine(lx, y_line, lx + loupe_diameter, y_line)

        center_cell_rect = QRect(
            int(lx + half_grid * cell_size),
            int(ly + half_grid * cell_size),
            int(cell_size),
            int(cell_size)
        )
        painter.setPen(QPen(QColor(255, 69, 58), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(center_cell_rect)

        info_rect = QRect(lx, ly + loupe_diameter, loupe_diameter, extra_h)
        painter.fillRect(info_rect, QColor(15, 23, 42, 255))

        swatch_rect = QRect(lx + 8, ly + loupe_diameter + 6, 16, 16)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(QBrush(pixel_color))
        painter.drawRoundedRect(swatch_rect, 3, 3)

        font = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(241, 245, 249))

        text_str = f"{hex_color}  ({px}, {py})"
        text_rect = QRect(lx + 30, ly + loupe_diameter, loupe_diameter - 34, extra_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text_str)

        painter.restore()
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(container_path)

    def _reset_selection(self):
        self.state = OverlayState.READY
        self.selection_rect = QRect()
        self.annotations.clear()
        self._step_counter = 1
        self._cached_processed_pixmap = None
        self.toolbar.hide()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def _confirm_to_clipboard(self):
        final_pixmap = self._get_current_image()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setPixmap(final_pixmap)
        self.confirmed.emit(final_pixmap, self.selection_rect)
        self.close()

    def _cancel(self):
        self.cancelled.emit()
        self.close()
