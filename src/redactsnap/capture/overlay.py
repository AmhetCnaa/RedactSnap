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
from pathlib import Path
from datetime import datetime
from PIL import Image

from PyQt6.QtWidgets import QWidget, QApplication, QFileDialog
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer
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
from ..redaction.worker import RedactionWorker
from ..redaction.detector import RedactionTarget
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

        # Live transformation state & multi-tier caching (60 FPS smooth)
        self._is_redacted = False
        self._current_preset_idx = -1
        self._redaction_pipeline: Optional[RedactionPipeline] = None

        # Multi-tier pixmap caching:
        self._base_cropped_pixmap: Optional[QPixmap] = None      # Clean unredacted crop
        self._cached_redacted_pixmap: Optional[QPixmap] = None   # Redacted crop from background worker
        self._cached_composite_pixmap: Optional[QPixmap] = None  # (redacted/base) + annotations + frame
        self._cached_targets: List[RedactionTarget] = []

        # Async background redaction state
        self._current_scan_id: int = 0
        self._redaction_worker: Optional[RedactionWorker] = None
        self._stale_workers: List[RedactionWorker] = []
        self._is_scanning: bool = False

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

    def apply_tray_settings(self, auto_redact: bool = False, preset_id: Optional[str] = None):
        """Synchronizes default state from the persistent system tray settings."""
        self._is_redacted = auto_redact
        self.toolbar.set_redact_active(auto_redact)

        if preset_id and preset_id != "off":
            for idx, p in enumerate(PRESETS):
                if p.id == preset_id:
                    self._current_preset_idx = idx
                    self.toolbar.btn_beautify.setText(f"🎨 {p.name}")
                    break
        else:
            self._current_preset_idx = -1
            self.toolbar.btn_beautify.setText("🎨 Frame")

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
                self._cached_composite_pixmap = None
                self._step_counter += 1
                self.state = OverlayState.SELECTED
                self.update()
            return

        if self.state in (OverlayState.SELECTED, OverlayState.ANNOTATING):
            handle = self._hit_test_handle(pos)
            if handle != ResizeHandle.NONE:
                self._abort_active_redaction_scan()
                self.state = OverlayState.RESIZING
                self.active_handle = handle
                self.origin_point = pos
                self.toolbar.hide()
                return

            if self.selection_rect.contains(pos):
                self._abort_active_redaction_scan()
                self.state = OverlayState.MOVING
                self.move_offset = pos - self.selection_rect.topLeft()
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.toolbar.hide()
                return

        # Start fresh selection
        self._abort_active_redaction_scan()
        self.state = OverlayState.DRAGGING
        self.origin_point = pos
        self.current_point = pos
        self.selection_rect = QRect(pos, QSize(0, 0))
        self.annotations.clear()
        self._step_counter = 1
        self._base_cropped_pixmap = None
        self._cached_redacted_pixmap = None
        self._cached_composite_pixmap = None
        self._cached_targets.clear()
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
                    self._cached_composite_pixmap = None

                self._anno_start_pos = None
                self.state = OverlayState.SELECTED
                self.update()
                return

            if self.state in (OverlayState.DRAGGING, OverlayState.MOVING, OverlayState.RESIZING):
                if self.selection_rect.width() >= 12 and self.selection_rect.height() >= 12:
                    self.state = OverlayState.SELECTED
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.toolbar.anchor_to_selection(self.selection_rect, self.rect())

                    # Cache base crop instantly (0ms UI latency)
                    self._base_cropped_pixmap = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
                    self._cached_redacted_pixmap = None
                    self._cached_composite_pixmap = None
                    self._cached_targets.clear()

                    # Launch async background OCR & redaction without blocking UI
                    if self._is_redacted:
                        self._start_async_redaction(self._base_cropped_pixmap)
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
            dx, dy = 0, 0
            if key == Qt.Key.Key_Left:
                dx = -step
            elif key == Qt.Key.Key_Right:
                dx = step
            elif key == Qt.Key.Key_Up:
                dy = -step
            elif key == Qt.Key.Key_Down:
                dy = step

            if dx != 0 or dy != 0:
                moved_rect = self.selection_rect.translated(dx, dy)
                # Clamp within virtual desktop bounds
                screen_rect = self.rect()
                if moved_rect.left() < screen_rect.left():
                    moved_rect.moveLeft(screen_rect.left())
                if moved_rect.right() > screen_rect.right():
                    moved_rect.moveRight(screen_rect.right())
                if moved_rect.top() < screen_rect.top():
                    moved_rect.moveTop(screen_rect.top())
                if moved_rect.bottom() > screen_rect.bottom():
                    moved_rect.moveBottom(screen_rect.bottom())

                self.selection_rect = moved_rect
                self._base_cropped_pixmap = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
                self._cached_redacted_pixmap = None
                self._cached_composite_pixmap = None

                if self._is_redacted:
                    self._start_async_redaction(self._base_cropped_pixmap)

                self.toolbar.anchor_to_selection(self.selection_rect, self.rect())
                self.update()

    # --------------------------------------------------------------------------
    # Handlers & Actions
    # --------------------------------------------------------------------------

    def _get_current_image(self) -> QPixmap:
        """Composites cropped selection with redactions, annotations, and beautifier with zero synchronous OCR."""
        if self._cached_composite_pixmap is not None:
            return self._cached_composite_pixmap

        # 1. Base layer: redacted pixmap if active & available, otherwise clean base crop
        if self._is_redacted and self._cached_redacted_pixmap is not None:
            base_pixmap = self._cached_redacted_pixmap
        else:
            if self._base_cropped_pixmap is None:
                self._base_cropped_pixmap = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
            base_pixmap = self._base_cropped_pixmap

        # Fast path if no annotations and no frame preset applied
        if not self.annotations and self._current_preset_idx < 0:
            self._cached_composite_pixmap = base_pixmap
            return self._cached_composite_pixmap

        pil_img = ScreenGrabber.pixmap_to_pil(base_pixmap)

        # 2. Annotations
        if self.annotations:
            pil_img = AnnotationRenderer.render_on_image(pil_img, self.annotations)

        # 3. Studio Beautification
        if self._current_preset_idx >= 0:
            preset = PRESETS[self._current_preset_idx]
            config = StudioConfig(preset=preset, padding=40, show_window_chrome=True, corner_radius=12)
            pil_img = StudioBeautifier.render(pil_img, config)

        self._cached_composite_pixmap = ScreenGrabber.pil_to_pixmap(pil_img)
        return self._cached_composite_pixmap

    def _abort_active_redaction_scan(self):
        """Aborts active background worker safely without QThread GC crash."""
        if self._redaction_worker is not None:
            worker = self._redaction_worker
            self._redaction_worker = None
            worker.abort()
            try:
                worker.finished.disconnect()
            except Exception:
                pass
            try:
                worker.failed.disconnect()
            except Exception:
                pass

            if worker.isRunning():
                self._stale_workers.append(worker)

                def _cleanup_stale(w=worker):
                    if w in self._stale_workers:
                        self._stale_workers.remove(w)
                    w.deleteLater()

                worker.finished.connect(_cleanup_stale)
            else:
                worker.deleteLater()

        self._is_scanning = False

    def _start_async_redaction(self, cropped_pixmap: Optional[QPixmap] = None):
        """Launches OCR and secret detection asynchronously in a background QThread."""
        self._abort_active_redaction_scan()

        if cropped_pixmap is None:
            if self._base_cropped_pixmap is None:
                self._base_cropped_pixmap = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
            cropped_pixmap = self._base_cropped_pixmap

        if self._redaction_pipeline is None:
            self._redaction_pipeline = RedactionPipeline()

        self._current_scan_id += 1
        scan_id = self._current_scan_id
        pil_img = ScreenGrabber.pixmap_to_pil(cropped_pixmap)

        self._is_scanning = True
        self.toolbar.btn_redact.setText("⏳ Scanning...")

        worker = RedactionWorker(scan_id, pil_img, self._redaction_pipeline, parent=self)
        self._redaction_worker = worker

        def _on_finished(s_id, redacted_pil, targets):
            self._on_redaction_worker_finished(s_id, redacted_pil, targets)
            if self._redaction_worker is worker:
                self._redaction_worker = None
            worker.deleteLater()

        def _on_failed(s_id, err_msg):
            self._on_redaction_worker_failed(s_id, err_msg)
            if self._redaction_worker is worker:
                self._redaction_worker = None
            worker.deleteLater()

        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        worker.start()

    def _on_redaction_worker_finished(self, scan_id: int, redacted_pil: Image.Image, targets: list):
        if scan_id != self._current_scan_id:
            return  # Stale scan from an older selection, ignore

        self._cached_redacted_pixmap = ScreenGrabber.pil_to_pixmap(redacted_pil)
        self._cached_targets = targets
        self._cached_composite_pixmap = None
        self._is_scanning = False

        count = len(targets)
        self.toolbar.set_redact_active(True, count=count)
        if count > 0:
            self.toast.show_message(f"🛡️ Auto-redacted {count} secret(s)!", 2000)
        self.update()

    def _on_redaction_worker_failed(self, scan_id: int, err_msg: str):
        if scan_id != self._current_scan_id:
            return
        self._is_scanning = False
        self.toolbar.set_redact_active(True, count=0)
        self.update()

    def _on_redact_toggled(self, active: bool):
        self._is_redacted = active
        self._cached_composite_pixmap = None

        if active:
            if self._cached_redacted_pixmap is not None:
                count = len(self._cached_targets)
                self.toolbar.set_redact_active(True, count=count)
                msg = f"🛡️ Auto-redacted {count} secret(s)!" if count > 0 else "ℹ️ No sensitive secrets detected"
                self.toast.show_message(msg, 1500)
            else:
                if self._base_cropped_pixmap is None:
                    self._base_cropped_pixmap = ScreenGrabber.crop_region(self.virtual_pixmap, self.selection_rect)
                self._start_async_redaction(self._base_cropped_pixmap)
        else:
            self.toolbar.set_redact_active(False)
            self.toast.show_message("🛡️ Redaction hidden", 1200)

        self.update()

    def _on_beautify_cycle(self):
        self._current_preset_idx += 1
        if self._current_preset_idx >= len(PRESETS):
            self._current_preset_idx = -1

        self._cached_composite_pixmap = None

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
            self._cached_composite_pixmap = None
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
        if self._is_scanning and self._is_redacted and self._redaction_worker is not None:
            self._redaction_worker.wait(1200)

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

    @staticmethod
    def get_default_screenshots_dir() -> Path:
        """Locates or creates the standard user Screenshots directory (Pictures/Screenshots)."""
        pictures = Path.home() / "Pictures"
        screenshots_dir = pictures / "Screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        return screenshots_dir

    def _auto_save_and_confirm(self):
        """
        Instant Auto-Save: Saves to Pictures/Screenshots/RedactSnap_YYYYMMDD_HHMMSS.png,
        simultaneously copies to system clipboard, emits confirmed signal, and closes overlay.
        Matches Windows Snipping Tool / CleanShot X standard.
        """
        if self._is_scanning and self._is_redacted and self._redaction_worker is not None:
            self._redaction_worker.wait(1200)

        final_pixmap = self._get_current_image()

        # 1. Instant Auto-save to Pictures/Screenshots
        saved_path = None
        try:
            screenshots_dir = self.get_default_screenshots_dir()
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = screenshots_dir / f"RedactSnap_{now_str}.png"
            if target_file.exists():
                target_file = screenshots_dir / f"RedactSnap_{now_str}_{datetime.now().microsecond // 1000:03d}.png"
            final_pixmap.save(str(target_file), "PNG")
            saved_path = str(target_file)
            print(f"[RedactSnap] Saved screenshot to: {saved_path}")
        except Exception as e:
            print(f"[RedactSnap] Warning: Could not auto-save to Screenshots: {e}")

        # 2. Copy to clipboard
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setPixmap(final_pixmap)

        # 3. Toast HUD & Close
        self.toast.show_message("✓ Saved to Screenshots & Copied!", 2000)
        self.confirmed.emit(final_pixmap, self.selection_rect)
        self.close()

    def _on_save_clicked(self):
        self._auto_save_and_confirm()

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
            if self._is_redacted and self._cached_redacted_pixmap is not None:
                painter.drawPixmap(self.selection_rect, self._cached_redacted_pixmap)
            else:
                painter.drawPixmap(self.selection_rect, self.virtual_pixmap, self.selection_rect)

            # Draw subtle theme frame preview outside selection if studio preset active
            if 0 <= self._current_preset_idx < len(PRESETS):
                preset = PRESETS[self._current_preset_idx]
                theme_color = QColor(preset.gradient_stops[0])
                frame_pen = QPen(theme_color, 3)
                painter.setPen(frame_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(self.selection_rect.adjusted(-4, -4, 4, 4), 6, 6)

            # Draw live annotations
            if self.annotations:
                AnnotationRenderer.render_with_qpainter(
                    painter,
                    self.annotations,
                    origin_offset=(self.selection_rect.x(), self.selection_rect.y())
                )

            # Draw active in-progress annotation preview
            if (
                self.state == OverlayState.ANNOTATING
                and self._anno_start_pos is not None
                and self.active_anno_tool is not None
            ):
                rel_start = (
                    self._anno_start_pos.x() - self.selection_rect.x(),
                    self._anno_start_pos.y() - self.selection_rect.y()
                )
                rel_curr = (
                    self.current_point.x() - self.selection_rect.x(),
                    self.current_point.y() - self.selection_rect.y()
                )
                temp_anno = Annotation(
                    type=self.active_anno_tool,
                    start_pos=rel_start,
                    end_pos=rel_curr,
                    text=str(self._step_counter) if self.active_anno_tool == AnnotationType.STEP_NUMBER else ""
                )
                AnnotationRenderer.render_with_qpainter(
                    painter,
                    [temp_anno],
                    origin_offset=(self.selection_rect.x(), self.selection_rect.y())
                )

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
        self._abort_active_redaction_scan()
        self.state = OverlayState.READY
        self.selection_rect = QRect()
        self.annotations.clear()
        self._step_counter = 1
        self._base_cropped_pixmap = None
        self._cached_redacted_pixmap = None
        self._cached_composite_pixmap = None
        self._cached_targets.clear()
        self.toolbar.hide()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def _confirm_to_clipboard(self):
        self._auto_save_and_confirm()

    def _cancel(self):
        if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
            try:
                self.recorder.cancel()
            except Exception:
                pass
        if hasattr(self, '_upload_worker') and self._upload_worker and self._upload_worker.isRunning():
            try:
                self._upload_worker.wait(500)
            except Exception:
                pass
        self._abort_active_redaction_scan()
        for w in list(self._stale_workers):
            if w.isRunning():
                w.abort()
                w.wait(200)
        self._stale_workers.clear()
        self.cancelled.emit()
        self.close()

    def closeEvent(self, event):
        if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
            try:
                self.recorder.cancel()
            except Exception:
                pass
        if hasattr(self, '_upload_worker') and self._upload_worker and self._upload_worker.isRunning():
            try:
                self._upload_worker.wait(500)
            except Exception:
                pass
        self._abort_active_redaction_scan()
        for w in list(self._stale_workers):
            if w.isRunning():
                w.abort()
                w.wait(200)
        self._stale_workers.clear()
        super().closeEvent(event)
