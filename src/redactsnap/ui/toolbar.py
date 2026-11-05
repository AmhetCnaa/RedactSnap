"""
Floating Action Bar for RedactSnap v0.5.0.
Provides a modern glassmorphism quick-action bar with:
- Image Copy, Save, and Live Redaction
- Social Studio Canvas Themes
- 1-Click Offline OCR
- Smart Annotations (Step Numbers, Arrows, Highlighter, Spotlight)
- Live Screen Recording (GIF/MP4) with mini timer
- Zero-Server Instant Link Sharing (Imgur / S3)
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QFont

from ..studio.annotations import AnnotationType


class FloatingToolbar(QWidget):
    """
    Floating toolbar with CleanShot-grade glassmorphism styling and sub-menus.
    """

    copy_clicked = pyqtSignal()
    redact_toggled = pyqtSignal(bool)
    beautify_cycle = pyqtSignal()
    ocr_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    upload_clicked = pyqtSignal()
    record_toggle = pyqtSignal(bool)
    annotation_selected = pyqtSignal(object)
    undo_annotation = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._is_redacted = False
        self._current_preset_name = "Off"
        self._is_recording = False
        self._active_annotation_tool: Optional[AnnotationType] = None
        self._show_annotation_subbar = False

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(4)

        # ----------------------------------------------------------------------
        # Sub-bar for Annotations (Appears above main toolbar when toggled)
        # ----------------------------------------------------------------------
        self.anno_frame = QFrame(self)
        self.anno_frame.setObjectName("sub_frame")
        anno_layout = QHBoxLayout(self.anno_frame)
        anno_layout.setContentsMargins(6, 3, 6, 3)
        anno_layout.setSpacing(4)

        self.btn_anno_step = QPushButton("① Step", self.anno_frame)
        self.btn_anno_step.clicked.connect(lambda: self._select_anno_tool(AnnotationType.STEP_NUMBER))
        anno_layout.addWidget(self.btn_anno_step)

        self.btn_anno_arrow = QPushButton("➡️ Arrow", self.anno_frame)
        self.btn_anno_arrow.clicked.connect(lambda: self._select_anno_tool(AnnotationType.ARROW))
        anno_layout.addWidget(self.btn_anno_arrow)

        self.btn_anno_rect = QPushButton("🔲 Box", self.anno_frame)
        self.btn_anno_rect.clicked.connect(lambda: self._select_anno_tool(AnnotationType.RECTANGLE))
        anno_layout.addWidget(self.btn_anno_rect)

        self.btn_anno_highlighter = QPushButton("🖍️ Highlight", self.anno_frame)
        self.btn_anno_highlighter.clicked.connect(lambda: self._select_anno_tool(AnnotationType.HIGHLIGHTER))
        anno_layout.addWidget(self.btn_anno_highlighter)

        self.btn_anno_spotlight = QPushButton("💡 Spotlight", self.anno_frame)
        self.btn_anno_spotlight.clicked.connect(lambda: self._select_anno_tool(AnnotationType.SPOTLIGHT))
        anno_layout.addWidget(self.btn_anno_spotlight)

        self.btn_anno_undo = QPushButton("↩️ Undo", self.anno_frame)
        self.btn_anno_undo.clicked.connect(self.undo_annotation.emit)
        anno_layout.addWidget(self.btn_anno_undo)

        self.anno_frame.hide()
        root_layout.addWidget(self.anno_frame)

        # ----------------------------------------------------------------------
        # Main Toolbar Frame
        # ----------------------------------------------------------------------
        self.frame = QFrame(self)
        self.frame.setObjectName("toolbar_frame")
        self.frame_layout = QHBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(6, 4, 6, 4)
        self.frame_layout.setSpacing(4)

        # 1. Copy Image
        self.btn_copy = QPushButton("📋 Copy", self.frame)
        self.btn_copy.setToolTip("Copy image to clipboard (Enter / Ctrl+C)")
        self.btn_copy.clicked.connect(self.copy_clicked.emit)
        self.frame_layout.addWidget(self.btn_copy)

        # Separator
        self.frame_layout.addWidget(self._create_separator())

        # 2. Auto Redact Toggle
        self.btn_redact = QPushButton("🛡️ Redact", self.frame)
        self.btn_redact.setToolTip("Auto-detect and censor API keys, secrets, emails, and PII")
        self.btn_redact.clicked.connect(self._toggle_redact)
        self.frame_layout.addWidget(self.btn_redact)

        # 3. Beautify Cycle
        self.btn_beautify = QPushButton("🎨 Frame: Off", self.frame)
        self.btn_beautify.setToolTip("Cycle aesthetic social canvas frames (Obsidian, Sunset, etc.)")
        self.btn_beautify.clicked.connect(self.beautify_cycle.emit)
        self.frame_layout.addWidget(self.btn_beautify)

        # 4. Annotations Toggle
        self.btn_annotate = QPushButton("✏️ Draw", self.frame)
        self.btn_annotate.setToolTip("Add arrows, step numbers, highlights, and spotlights")
        self.btn_annotate.clicked.connect(self._toggle_annotation_bar)
        self.frame_layout.addWidget(self.btn_annotate)

        # Separator
        self.frame_layout.addWidget(self._create_separator())

        # 5. Copy as Text (OCR)
        self.btn_ocr = QPushButton("📝 OCR", self.frame)
        self.btn_ocr.setToolTip("Extract all text from image directly to clipboard (100% Offline)")
        self.btn_ocr.clicked.connect(self.ocr_clicked.emit)
        self.frame_layout.addWidget(self.btn_ocr)

        # 6. Screen Record (GIF/MP4)
        self.btn_record = QPushButton("⏺ Record", self.frame)
        self.btn_record.setToolTip("Record live screen area to animated GIF / MP4")
        self.btn_record.clicked.connect(self._toggle_record)
        self.frame_layout.addWidget(self.btn_record)

        # 7. Upload & Share Link
        self.btn_upload = QPushButton("🔗 Share", self.frame)
        self.btn_upload.setToolTip("Upload and get instant shareable link (Imgur / S3)")
        self.btn_upload.clicked.connect(self.upload_clicked.emit)
        self.frame_layout.addWidget(self.btn_upload)

        # 8. Save
        self.btn_save = QPushButton("💾 Save", self.frame)
        self.btn_save.setToolTip("Save image to file (Ctrl+S)")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.frame_layout.addWidget(self.btn_save)

        # Separator
        self.frame_layout.addWidget(self._create_separator())

        # 9. Cancel
        self.btn_cancel = QPushButton("✕", self.frame)
        self.btn_cancel.setToolTip("Cancel and close overlay (Escape)")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        self.frame_layout.addWidget(self.btn_cancel)

        root_layout.addWidget(self.frame)

        self._apply_styles()
        self.adjustSize()
        self.hide()

    def _create_separator(self) -> QFrame:
        sep = QFrame(self.frame)
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        return sep

    def _apply_styles(self):
        self.setStyleSheet("""
            QFrame#toolbar_frame, QFrame#sub_frame {
                background-color: rgba(15, 23, 42, 238);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 12px;
            }
            QPushButton {
                background-color: transparent;
                color: #E2E8F0;
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 6px 11px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 28);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 50);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 15);
            }
            QFrame#separator {
                background-color: rgba(255, 255, 255, 30);
                width: 1px;
                max-width: 1px;
                margin: 4px 2px;
            }
        """)

    def _toggle_redact(self):
        self._is_redacted = not self._is_redacted
        self.set_redact_active(self._is_redacted)
        self.redact_toggled.emit(self._is_redacted)

    def set_redact_active(self, active: bool, count: Optional[int] = None):
        self._is_redacted = active
        if active:
            label = f"🛡️ Redacted ({count})" if count is not None else "🛡️ Redacted"
            self.btn_redact.setText(label)
            self.btn_redact.setStyleSheet("""
                background-color: #0A84FF;
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 7px;
            """)
        else:
            self.btn_redact.setText("🛡️ Redact")
            self.btn_redact.setStyleSheet("")

    def set_beautify_preset(self, preset_name: str):
        self._current_preset_name = preset_name
        self.btn_beautify.setText(f"🎨 Frame: {preset_name}")
        if preset_name != "Off":
            self.btn_beautify.setStyleSheet("""
                background-color: rgba(124, 58, 237, 180);
                color: #FFFFFF;
                border: 1px solid #C084FC;
                border-radius: 7px;
            """)
        else:
            self.btn_beautify.setStyleSheet("")

    def _toggle_annotation_bar(self):
        self._show_annotation_subbar = not self._show_annotation_subbar
        if self._show_annotation_subbar:
            self.anno_frame.show()
            self.btn_annotate.setStyleSheet("background-color: rgba(255, 255, 255, 30); color: #38BDF8;")
        else:
            self.anno_frame.hide()
            self.btn_annotate.setStyleSheet("")
            self._select_anno_tool(None)
        self.adjustSize()

    def _select_anno_tool(self, tool: Optional[AnnotationType]):
        self._active_annotation_tool = tool
        self.annotation_selected.emit(tool)

        # Update button highlights
        buttons = {
            AnnotationType.STEP_NUMBER: self.btn_anno_step,
            AnnotationType.ARROW: self.btn_anno_arrow,
            AnnotationType.RECTANGLE: self.btn_anno_rect,
            AnnotationType.HIGHLIGHTER: self.btn_anno_highlighter,
            AnnotationType.SPOTLIGHT: self.btn_anno_spotlight,
        }
        for t, btn in buttons.items():
            if t == tool:
                btn.setStyleSheet("background-color: #0A84FF; color: white;")
            else:
                btn.setStyleSheet("")

    def _toggle_record(self):
        self._is_recording = not self._is_recording
        if self._is_recording:
            self.btn_record.setText("⏹ Stop")
            self.btn_record.setStyleSheet("background-color: #EF4444; color: white; border: 1px solid #F87171;")
        else:
            self.btn_record.setText("⏺ Record")
            self.btn_record.setStyleSheet("")
        self.record_toggle.emit(self._is_recording)

    def update_record_timer(self, seconds: int):
        mins = seconds // 60
        secs = seconds % 60
        self.btn_record.setText(f"⏹ {mins:02d}:{secs:02d}")

    def anchor_to_selection(self, selection_rect: QRect, bounds_rect: QRect):
        self.adjustSize()
        w = self.width()
        h = self.height()

        cx = selection_rect.center().x()
        x = cx - (w // 2)
        x = max(10, min(x, bounds_rect.width() - w - 10))

        y = selection_rect.bottom() + 14
        if y + h > bounds_rect.height() - 10:
            y = selection_rect.top() - h - 14

        self.move(x, y)
        self.show()
        self.raise_()
