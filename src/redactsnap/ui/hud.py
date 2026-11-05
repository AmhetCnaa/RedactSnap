"""
HUD Toast notification component for RedactSnap.
Provides non-intrusive floating feedback messages with smooth auto-dismissal.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor, QFont


class ToastHUD(QWidget):
    """
    Floating pill notification for user feedback (e.g. '✓ Text copied to clipboard').
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 8, 16, 8)

        self.label = QLabel(self)
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self.setStyleSheet("""
            ToastHUD {
                background-color: rgba(15, 23, 42, 240);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 18px;
            }
            QLabel {
                color: #F8FAFC;
                background: transparent;
            }
        """)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

        self.hide()

    def show_message(self, message: str, duration_ms: int = 1800, pos: Optional[QPoint] = None):
        """Displays toast message with smooth fade in."""
        self.label.setText(message)
        self.adjustSize()

        if pos is not None:
            self.move(pos.x() - self.width() // 2, pos.y())
        elif self.parentWidget() is not None:
            # Default to top center of parent
            parent_w = self.parentWidget().width()
            self.move((parent_w - self.width()) // 2, 40)

        self.show()
        self.raise_()

        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(1.0)
        self.anim.start()

        self.hide_timer.start(duration_ms)

    def fade_out(self):
        """Smoothly fades out and hides."""
        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._on_fade_out_finished)
        self.anim.start()

    def _on_fade_out_finished(self):
        try:
            self.anim.finished.disconnect(self._on_fade_out_finished)
        except TypeError:
            pass
        self.hide()
