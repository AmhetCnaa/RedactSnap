"""
Background QThread worker for non-blocking OCR and redaction scanning.
"""

from typing import List, Optional
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal

from .engine import RedactionPipeline
from .detector import RedactionTarget
from .masker import RedactionStyle


class RedactionWorker(QThread):
    """
    Executes heavy OCR inference and redaction in an isolated background thread,
    keeping the PyQt6 UI completely responsive (60 FPS smooth).
    """

    finished = pyqtSignal(int, object, list)  # scan_id, redacted_pil_image, targets
    failed = pyqtSignal(int, str)             # scan_id, error_message

    def __init__(
        self,
        scan_id: int,
        image: Image.Image,
        pipeline: RedactionPipeline,
        parent=None
    ):
        super().__init__(parent)
        self.scan_id = scan_id
        self.image = image
        self.pipeline = pipeline
        self._is_aborted = False

    def abort(self):
        """Signals the worker to discard results and stop gracefully."""
        self._is_aborted = True

    def run(self):
        try:
            if self._is_aborted:
                return

            redacted_img, targets = self.pipeline.process(
                self.image,
                style=RedactionStyle.GAUSSIAN_BLUR
            )

            if self._is_aborted:
                return

            self.finished.emit(self.scan_id, redacted_img, targets)
        except BaseException as e:
            if not self._is_aborted:
                self.failed.emit(self.scan_id, str(e))
