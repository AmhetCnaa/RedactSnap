"""
Unit tests for the UI components: FloatingToolbar, ToastHUD, and System Tray.
"""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint

from redactsnap.ui.hud import ToastHUD
from redactsnap.ui.toolbar import FloatingToolbar
from redactsnap.ui.tray import create_tray_icon_pixmap, SystemTrayManager
from redactsnap.hotkey.manager import HotkeyManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_toast_hud(qapp):
    hud = ToastHUD()
    assert hud.isHidden()

    hud.show_message("Test Message", duration_ms=1000)
    assert hud.isVisible()
    assert hud.label.text() == "Test Message"


def test_floating_toolbar_actions(qapp):
    toolbar = FloatingToolbar()
    assert toolbar.isHidden()

    copy_called = []
    redact_called = []
    beautify_called = []
    ocr_called = []

    toolbar.copy_clicked.connect(lambda: copy_called.append(True))
    toolbar.redact_toggled.connect(lambda active: redact_called.append(active))
    toolbar.beautify_cycle.connect(lambda: beautify_called.append(True))
    toolbar.ocr_clicked.connect(lambda: ocr_called.append(True))

    toolbar.btn_copy.click()
    assert len(copy_called) == 1

    # Since redact is enabled by default, clicking it toggles it to False
    toolbar.btn_redact.click()
    assert len(redact_called) == 1
    assert redact_called[0] is False

    toolbar.btn_beautify.click()
    assert len(beautify_called) == 1

    toolbar.btn_ocr.click()
    assert len(ocr_called) == 1


def test_toolbar_anchoring(qapp):
    toolbar = FloatingToolbar()
    bounds = QRect(0, 0, 1920, 1080)
    selection = QRect(200, 200, 400, 300)

    toolbar.anchor_to_selection(selection, bounds)
    assert toolbar.isVisible()

    # Toolbar should be centered horizontally with selection
    expected_x = selection.center().x() - toolbar.width() // 2
    assert toolbar.x() == expected_x
    # Toolbar should be below selection
    assert toolbar.y() == selection.bottom() + 14


def test_tray_icon_generation(qapp):
    pixmap = create_tray_icon_pixmap()
    assert not pixmap.isNull()
    assert pixmap.width() == 64
    assert pixmap.height() == 64


def test_hotkey_manager_initialization(qapp):
    hm = HotkeyManager()
    assert hm._listener is None
