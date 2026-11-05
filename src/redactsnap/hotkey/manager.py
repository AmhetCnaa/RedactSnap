"""
Global hotkey manager for RedactSnap.
Listens for system-wide shortcuts (PrintScreen, Ctrl+Shift+S) in a background thread
and safely communicates with the PyQt event loop.
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard


class HotkeyManager(QObject):
    """
    Background hotkey daemon emitting Qt signals when shortcuts are triggered.
    """

    trigger_capture = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self):
        """Starts background keyboard listener."""
        if self._listener is not None:
            return

        hotkeys = {
            "<print_screen>": self._on_triggered,
            "<ctrl>+<shift>+s": self._on_triggered,
        }

        try:
            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            print("[RedactSnap] Global hotkeys active: [PrintScreen] and [Ctrl+Shift+S]")
        except Exception as e:
            print(f"[RedactSnap] Warning: Could not register global hotkeys: {e}")

    def stop(self):
        """Stops background keyboard listener."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_triggered(self):
        """Callback invoked by pynput on key event (cross-thread)."""
        self.trigger_capture.emit()
