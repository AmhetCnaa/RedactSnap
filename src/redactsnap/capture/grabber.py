"""
Screen grabber module for RedactSnap.
Provides high-performance multi-monitor virtual desktop capture using Qt native APIs
with zero-copy conversion to PIL and NumPy formats.
"""

from typing import Tuple, List, Optional
import numpy as np
from PIL import Image

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication, QPixmap, QImage, QPainter
from PyQt6.QtCore import QRect, QPoint, QSize


class ScreenGrabber:
    """
    Handles screen capture across arbitrary multi-monitor topologies
    (differing DPI scales, resolutions, and relative positions).
    """

    @classmethod
    def get_virtual_desktop_rect(cls) -> QRect:
        """Computes the bounding rectangle encompassing all connected screens."""
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)

        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        return total_rect

    @classmethod
    def capture_virtual_desktop(cls) -> Tuple[QPixmap, QRect]:
        """
        Takes a synchronized snapshot of all monitors and stitches them
        into a single contiguous virtual desktop QPixmap.

        Returns:
            Tuple of (virtual_pixmap, virtual_desktop_rect)
        """
        screens = QGuiApplication.screens()
        total_rect = cls.get_virtual_desktop_rect()

        virtual_pixmap = QPixmap(total_rect.size())
        virtual_pixmap.fill(Qt_transparent_color())

        painter = QPainter(virtual_pixmap)
        try:
            for screen in screens:
                geom = screen.geometry()
                # Grab the full window content of the screen
                screen_pixmap = screen.grabWindow(0)
                # Position relative to virtual desktop origin (which might be negative)
                offset_x = geom.x() - total_rect.x()
                offset_y = geom.y() - total_rect.y()
                painter.drawPixmap(offset_x, offset_y, screen_pixmap)
        finally:
            painter.end()

        return virtual_pixmap, total_rect

    @classmethod
    def crop_region(cls, pixmap: QPixmap, rect: QRect) -> QPixmap:
        """Crops a region from the virtual desktop pixmap."""
        normalized = rect.normalized()
        return pixmap.copy(normalized)

    @classmethod
    def pixmap_to_pil(cls, pixmap: QPixmap) -> Image.Image:
        """Converts a QPixmap to a PIL Image (RGBA) via raw buffer."""
        qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return Image.fromarray(arr.copy(), mode="RGBA")

    @classmethod
    def pil_to_pixmap(cls, pil_image: Image.Image) -> QPixmap:
        """Converts a PIL Image (RGB or RGBA) to a QPixmap with memory-safe deep buffer copy."""
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        return QPixmap.fromImage(qimage)

    @classmethod
    def pil_to_cv2(cls, pil_image: Image.Image) -> np.ndarray:
        """Converts a PIL Image (RGBA or RGB) to OpenCV BGR/BGRA numpy array."""
        arr = np.array(pil_image)
        if pil_image.mode == "RGBA":
            import cv2
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
        elif pil_image.mode == "RGB":
            import cv2
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr

    @classmethod
    def cv2_to_pil(cls, cv2_img: np.ndarray) -> Image.Image:
        """Converts an OpenCV BGR/BGRA numpy array to a PIL Image."""
        import cv2
        if len(cv2_img.shape) == 3 and cv2_img.shape[2] == 4:
            rgb_arr = cv2.cvtColor(cv2_img, cv2.COLOR_BGRA2RGBA)
            return Image.fromarray(rgb_arr, mode="RGBA")
        elif len(cv2_img.shape) == 3 and cv2_img.shape[2] == 3:
            rgb_arr = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb_arr, mode="RGB")
        return Image.fromarray(cv2_img)


def Qt_transparent_color():
    from PyQt6.QtGui import QColor
    return QColor(0, 0, 0, 0)
