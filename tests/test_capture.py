"""
Unit tests for the capture module.
"""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QColor, QPainter

from redactsnap.capture.grabber import ScreenGrabber
from redactsnap.capture.overlay import SnippingOverlay, OverlayState


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_virtual_desktop_rect(qapp):
    rect = ScreenGrabber.get_virtual_desktop_rect()
    assert rect.isValid()
    assert rect.width() > 0
    assert rect.height() > 0


def test_capture_virtual_desktop(qapp):
    pixmap, rect = ScreenGrabber.capture_virtual_desktop()
    assert not pixmap.isNull()
    assert pixmap.width() == rect.width()
    assert pixmap.height() == rect.height()


def test_crop_region(qapp):
    pixmap = QPixmap(200, 200)
    pixmap.fill(QColor("red"))

    crop_rect = QRect(10, 10, 50, 50)
    cropped = ScreenGrabber.crop_region(pixmap, crop_rect)
    assert cropped.width() == 50
    assert cropped.height() == 50


def test_conversions(qapp):
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(12, 34, 56, 255))

    # To PIL
    pil_img = ScreenGrabber.pixmap_to_pil(pixmap)
    assert pil_img.size == (100, 100)
    assert pil_img.mode == "RGBA"

    # PIL to Pixmap
    back_pixmap = ScreenGrabber.pil_to_pixmap(pil_img)
    assert back_pixmap.width() == 100
    assert back_pixmap.height() == 100

    # To CV2 and back
    cv2_img = ScreenGrabber.pil_to_cv2(pil_img)
    assert cv2_img.shape == (100, 100, 4)

    pil_again = ScreenGrabber.cv2_to_pil(cv2_img)
    assert pil_again.size == (100, 100)


def test_overlay_initialization(qapp):
    pixmap = QPixmap(800, 600)
    pixmap.fill(QColor("black"))
    rect = QRect(0, 0, 800, 600)

    overlay = SnippingOverlay(pixmap, rect)
    assert overlay.state == OverlayState.READY
    assert overlay.virtual_rect == rect
    assert overlay.selection_rect.isEmpty()


def test_overlay_mouse_and_keyboard_interaction(qapp):
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import Qt, QPoint

    pixmap = QPixmap(800, 600)
    pixmap.fill(QColor("blue"))
    rect = QRect(0, 0, 800, 600)

    overlay = SnippingOverlay(pixmap, rect)
    overlay.show()

    # Simulate mouse drag from (50, 50) to (250, 150)
    start_pos = QPoint(50, 50)
    end_pos = QPoint(250, 150)

    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start_pos)
    assert overlay.state == OverlayState.DRAGGING

    QTest.mouseMove(overlay, end_pos)
    # Note: In Qt QRect(QPoint, QPoint), coordinates are inclusive, so width = x2 - x1 + 1 (201 px)
    assert overlay.selection_rect.width() == 201
    assert overlay.selection_rect.height() == 101

    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end_pos)
    assert overlay.state == OverlayState.SELECTED
    assert overlay.selection_rect == QRect(50, 50, 201, 101)

    # Simulate arrow key nudge right by 1px
    QTest.keyClick(overlay, Qt.Key.Key_Right)
    assert overlay.selection_rect.left() == 51

    # Simulate Shift+Right nudge by 10px
    QTest.keyClick(overlay, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    assert overlay.selection_rect.left() == 61

    # Verify confirmation signal
    confirmed_data = []
    overlay.confirmed.connect(lambda pix, r: confirmed_data.append((pix, r)))

    QTest.keyClick(overlay, Qt.Key.Key_Return)
    assert len(confirmed_data) == 1
    cropped_pix, confirmed_rect = confirmed_data[0]
    assert cropped_pix.width() == 201
    assert cropped_pix.height() == 101
    assert confirmed_rect == QRect(61, 50, 201, 101)
