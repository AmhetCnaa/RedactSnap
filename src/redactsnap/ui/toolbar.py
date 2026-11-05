"""
Floating Action Bar for RedactSnap.
Provides a modern glassmorphism quick-action bar attached dynamically to the selection box.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QFont


class FloatingToolbar(QWidget):
    """
    Floating toolbar with CleanShot-grade glassmorphism styling.
    """

    copy_clicked = pyqtSignal()
    redact_toggled = pyqtSignal(bool)
    beautify_cycle = pyqtSignal()
    ocr_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._is_redacted = False
        self._current_preset_name = "Off"

        self._init_ui()

    def _init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame(self)
        self.frame.setObjectName("toolbar_frame")
        frame_layout = QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(6, 4, 6, 4)
        frame_layout.setSpacing(4)

        # 1. Copy Image
        self.btn_copy = QPushButton("📋 Copy", self.frame)
        self.btn_copy.setToolTip("Copy cropped/redacted image to clipboard (Enter / Ctrl+C)")
        self.btn_copy.clicked.connect(self.copy_clicked.emit)
        frame_layout.addWidget(self.btn_copy)

        # Separator
        frame_layout.addWidget(self._create_separator())

        # 2. Auto Redact Toggle
        self.btn_redact = QPushButton("🛡️ Redact", self.frame)
        self.btn_redact.setToolTip("Detect and censor API keys, secrets, emails, and PII")
        self.btn_redact.clicked.connect(self._toggle_redact)
        frame_layout.addWidget(self.btn_redact)

        # 3. Beautify Cycle
        self.btn_beautify = QPushButton("🎨 Frame: Off", self.frame)
        self.btn_beautify.setToolTip("Cycle aesthetic social canvas frames (Obsidian, Sunset, Cyber, etc.)")
        self.btn_beautify.clicked.connect(self.beautify_cycle.emit)
        frame_layout.addWidget(self.btn_beautify)

        # Separator
        frame_layout.addWidget(self._create_separator())

        # 4. Copy as Text (OCR)
        self.btn_ocr = QPushButton("📝 OCR Text", self.frame)
        self.btn_ocr.setToolTip("Extract all text from image directly to clipboard (100% Offline)")
        self.btn_ocr.clicked.connect(self.ocr_clicked.emit)
        frame_layout.addWidget(self.btn_ocr)

        # 5. Save to disk
        self.btn_save = QPushButton("💾 Save", self.frame)
        self.btn_save.setToolTip("Save image to file (Ctrl+S)")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        frame_layout.addWidget(self.btn_save)

        # Separator
        frame_layout.addWidget(self._create_separator())

        # 6. Cancel
        self.btn_cancel = QPushButton("✕", self.frame)
        self.btn_cancel.setToolTip("Cancel and close overlay (Escape)")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        frame_layout.addWidget(self.btn_cancel)

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
            QFrame#toolbar_frame {
                background-color: rgba(15, 23, 42, 235);
                border: 1px solid rgba(255, 255, 255, 50);
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
        """Updates redact button appearance."""
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
        """Updates the beautify button text."""
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

    def anchor_to_selection(self, selection_rect: QRect, bounds_rect: QRect):
        """
        Positions toolbar centered below selection, or above if close to bottom.
        """
        self.adjustSize()
        w = self.width()
        h = self.height()

        # Center horizontally
        cx = selection_rect.center().x()
        x = cx - (w // 2)

        # Clamp inside screen horizontally
        x = max(10, min(x, bounds_rect.width() - w - 10))

        # Position below selection by default
        y = selection_rect.bottom() + 14
        if y + h > bounds_rect.height() - 10:
            # Flip above selection
            y = selection_rect.top() - h - 14

        self.move(x, y)
        self.show()
        self.raise_()
