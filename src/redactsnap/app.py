"""
Application controller for RedactSnap.
Coordinates System Tray, Global Hotkeys, Screen Capture, and Overlay lifecycles.
"""

import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, Qt

from .capture.grabber import ScreenGrabber
from .capture.overlay import SnippingOverlay
from .ui.tray import SystemTrayManager
from .hotkey.manager import HotkeyManager


class RedactSnapApp(QObject):
    """
    Main application coordinator managing background hotkeys, system tray, and overlays.
    """

    def __init__(self, one_shot: bool = False, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.one_shot = one_shot
        self.active_overlay: Optional[SnippingOverlay] = None

        self.tray = SystemTrayManager()
        self.tray.capture_requested.connect(self.trigger_capture)
        self.tray.quit_requested.connect(self.quit_app)

        self.hotkeys = HotkeyManager()
        self.hotkeys.trigger_capture.connect(self.trigger_capture)

    def start(self):
        """Starts background hotkey listening and shows system tray."""
        if not self.one_shot:
            self.tray.show()
            self.hotkeys.start()
            self.tray.show_notification(
                "RedactSnap is Active 🚀",
                "Press [PrintScreen] or [Ctrl+Shift+S] to snip anytime."
            )
        else:
            self.trigger_capture()

    def trigger_capture(self):
        """Captures virtual desktop and presents the interactive overlay."""
        # Prevent opening multiple concurrent overlays
        if self.active_overlay is not None and self.active_overlay.isVisible():
            return

        print("[RedactSnap] Instant screen capture triggered (<15ms)...")
        virtual_pixmap, virtual_rect = ScreenGrabber.capture_virtual_desktop()

        self.active_overlay = SnippingOverlay(virtual_pixmap, virtual_rect)

        def on_confirmed(pixmap, rect):
            print(f"[RedactSnap] Capture completed: {rect.width()}x{rect.height()}")
            self.active_overlay = None
            if self.one_shot:
                self.quit_app()

        def on_cancelled():
            print("[RedactSnap] Capture dismissed.")
            self.active_overlay = None
            if self.one_shot:
                self.quit_app()

        self.active_overlay.confirmed.connect(on_confirmed)
        self.active_overlay.cancelled.connect(on_cancelled)

        self.active_overlay.show()
        self.active_overlay.raise_()
        self.active_overlay.activateWindow()

    def quit_app(self):
        """Gracefully terminates hotkey daemon and exits application."""
        self.hotkeys.stop()
        app = QApplication.instance()
        if app:
            app.quit()
