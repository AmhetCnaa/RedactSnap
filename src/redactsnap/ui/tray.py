"""
System Tray Manager for RedactSnap.
Provides a persistent background daemon, tray icon, context menu, and preferences.
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QAction, QActionGroup
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from .. import __version__
from ..studio.presets import PRESETS, get_preset_by_id


def create_tray_icon_pixmap() -> QPixmap:
    """Generates a crisp programmatic 64x64 lens/shield icon for the tray."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Gradient background circle (Apple Blue #0A84FF to Deep Navy #1E40AF)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(10, 132, 255)))
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    # Inner lens ring
    painter.setPen(QPen(QColor(255, 255, 255), 4))
    painter.setBrush(QBrush(QColor(15, 23, 42)))
    painter.drawEllipse(18, 18, 28, 28)

    # Shutter / Shield highlight dot
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(56, 189, 248)))
    painter.drawEllipse(28, 28, 8, 8)

    painter.end()
    return pixmap


class SystemTrayManager(QObject):
    """
    Manages the Windows taskbar system tray icon and background presence.
    """

    capture_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self.auto_redact_enabled = True
        self.selected_preset_id = "obsidian"

        self.tray_icon = QSystemTrayIcon(parent)
        self.icon_pixmap = create_tray_icon_pixmap()
        self.tray_icon.setIcon(QIcon(self.icon_pixmap))
        self.tray_icon.setToolTip("RedactSnap: Privacy-first Screenshot Autopilot")

        self._build_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _build_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.12);
                margin: 4px 6px;
            }
        """)

        # Action: Capture Screen
        action_capture = self.menu.addAction("📸 Capture Screen (PrintScreen)")
        action_capture.triggered.connect(self.capture_requested.emit)

        self.menu.addSeparator()

        # Action: Auto-Redact Toggle
        self.action_redact = QAction("🛡️ Auto-Redact Secrets by Default", self.menu)
        self.action_redact.setCheckable(True)
        self.action_redact.setChecked(self.auto_redact_enabled)
        self.action_redact.toggled.connect(self._on_redact_toggled)
        self.menu.addAction(self.action_redact)

        # Submenu: Presets
        presets_menu = self.menu.addMenu("🎨 Frame Preset")
        self.preset_group = QActionGroup(presets_menu)
        self.preset_group.setExclusive(True)

        # "Frame: Off" Option
        act_off = QAction("Frame: Off", presets_menu)
        act_off.setCheckable(True)
        act_off.setChecked(self.selected_preset_id in ("off", "", None))
        act_off.triggered.connect(lambda: self._set_preset("off"))
        self.preset_group.addAction(act_off)
        presets_menu.addAction(act_off)
        presets_menu.addSeparator()

        for preset in PRESETS:
            act = QAction(preset.name, presets_menu)
            act.setCheckable(True)
            act.setChecked(preset.id == self.selected_preset_id)
            act.triggered.connect(lambda checked, pid=preset.id: self._set_preset(pid))
            self.preset_group.addAction(act)
            presets_menu.addAction(act)

        self.menu.addSeparator()

        # Action: About
        action_about = self.menu.addAction("ℹ️ About RedactSnap")
        action_about.triggered.connect(self._show_about)

        # Action: Exit
        action_exit = self.menu.addAction("✕ Exit RedactSnap")
        action_exit.triggered.connect(self.quit_requested.emit)

        self.tray_icon.setContextMenu(self.menu)

    def show(self):
        self.tray_icon.show()

    def show_notification(self, title: str, message: str):
        """Displays native system notification bubble."""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2500)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.capture_requested.emit()

    def _on_redact_toggled(self, checked: bool):
        self.auto_redact_enabled = checked

    def _set_preset(self, preset_id: str):
        self.selected_preset_id = preset_id

    def _show_about(self):
        QMessageBox.about(
            None,
            "About RedactSnap",
            f"<h3>RedactSnap v{__version__}</h3>"
            "<p>Open-source, privacy-first desktop screenshot autopilot with automatic secret redaction, "
            "100% offline OCR, and social canvas beautification.</p>"
            "<p>CleanShot X alternative for Windows and Linux.</p>"
            "<p><b>Zero Cloud. 100% Local. Blazing Fast.</b></p>"
        )
