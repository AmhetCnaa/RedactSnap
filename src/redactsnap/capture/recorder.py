"""
Live screen recording and optimized GIF/MP4 export engine for RedactSnap.
Provides high-FPS capture with frame-buffering, real-time timer HUD, and pre-redaction masking.
"""

import os
import time
import tempfile
from typing import List, Optional, Tuple
from PIL import Image
import numpy as np
import cv2
import imageio

from PyQt6.QtCore import QObject, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPixmap

from .grabber import ScreenGrabber
from ..redaction.engine import RedactionPipeline
from ..redaction.masker import RedactionMasker, RedactionStyle


class ScreenRecorder(QObject):
    """
    Records a screen region into an optimized animated GIF or MP4 video.
    """

    tick = pyqtSignal(int)               # Emits elapsed seconds (e.g. 1, 2, 3...)
    frame_captured = pyqtSignal(int)    # Emits total frames captured
    finished = pyqtSignal(str, str)     # Emits (file_path, format)
    failed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.fps = 30
        self.output_format = "gif"
        self.auto_redact = False
        self.target_rect = QRect()

        self.frames: List[Image.Image] = []
        self._cached_redact_bboxes: List[Tuple[int, int, int, int]] = []
        self._redaction_pipeline: Optional[RedactionPipeline] = None

        self._start_time: float = 0.0
        self._elapsed_seconds: int = 0

        # Capture timer
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._capture_frame)

        # Seconds counter timer
        self._second_timer = QTimer(self)
        self._second_timer.timeout.connect(self._on_second_tick)

        self.is_recording = False

    def start(
        self,
        target_rect: QRect,
        fps: int = 30,
        output_format: str = "gif",
        auto_redact: bool = False
    ):
        """Starts real-time screen recording loop."""
        if self.is_recording:
            return

        self.target_rect = target_rect.normalized()
        self.fps = max(10, min(fps, 60))
        self.output_format = output_format.lower()
        self.auto_redact = auto_redact

        self.frames.clear()
        self._cached_redact_bboxes.clear()
        self._elapsed_seconds = 0
        self._start_time = time.time()
        self.is_recording = True

        interval_ms = max(16, 1000 // self.fps)
        self._capture_timer.start(interval_ms)
        self._second_timer.start(1000)

        # Immediate first frame capture
        self._capture_frame()

    def _capture_frame(self):
        """Grabs single frame from target rect and applies cached privacy masks."""
        if not self.is_recording:
            return

        # Fast direct capture of region
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        pix = screen.grabWindow(
            0,
            self.target_rect.x(),
            self.target_rect.y(),
            self.target_rect.width(),
            self.target_rect.height()
        )
        if pix.isNull():
            return

        pil_frame = ScreenGrabber.pixmap_to_pil(pix).convert("RGB")

        # In-flight privacy masking
        if self.auto_redact:
            if not self._cached_redact_bboxes:
                if self._redaction_pipeline is None:
                    self._redaction_pipeline = RedactionPipeline()
                targets, _ = self._redaction_pipeline.detector.scan(pil_frame)
                self._cached_redact_bboxes = [t.bbox for t in targets]

            if self._cached_redact_bboxes:
                pil_frame = RedactionMasker.apply_redaction(
                    pil_frame,
                    self._cached_redact_bboxes,
                    style=RedactionStyle.GAUSSIAN_BLUR
                ).convert("RGB")

        self.frames.append(pil_frame)
        self.frame_captured.emit(len(self.frames))

    def _on_second_tick(self):
        if self.is_recording:
            self._elapsed_seconds += 1
            self.tick.emit(self._elapsed_seconds)

    def stop(self, custom_output_path: Optional[str] = None) -> Optional[str]:
        """
        Stops recording loop and renders the buffered frames to file.
        Returns the output file path.
        """
        if not self.is_recording:
            return None

        self.is_recording = False
        self._capture_timer.stop()
        self._second_timer.stop()

        if not self.frames:
            self.failed.emit("No frames captured.")
            return None

        output_path = custom_output_path or self._get_default_output_path(self.output_format)

        try:
            if self.output_format == "gif":
                self._export_gif(output_path, self.frames, self.fps)
            elif self.output_format == "mp4":
                self._export_mp4(output_path, self.frames, self.fps)
            else:
                self._export_gif(output_path, self.frames, self.fps)

            self.finished.emit(output_path, self.output_format)
            return output_path

        except Exception as e:
            err_msg = f"Failed to export recording: {e}"
            self.failed.emit(err_msg)
            return None

    def cancel(self):
        """Aborts recording and discards frames."""
        self.is_recording = False
        self._capture_timer.stop()
        self._second_timer.stop()
        self.frames.clear()

    @staticmethod
    def _export_gif(output_path: str, frames: List[Image.Image], fps: int):
        """Exports frames to an optimized GIF using imageio or PIL."""
        # Convert frames to numpy arrays
        np_frames = [np.array(f) for f in frames]
        duration_sec = 1.0 / max(1, fps)
        imageio.mimsave(output_path, np_frames, format="GIF", duration=duration_sec, loop=0)

    @staticmethod
    def _export_mp4(output_path: str, frames: List[Image.Image], fps: int):
        """Exports frames to MP4 using OpenCV VideoWriter."""
        if not frames:
            return
        w, h = frames[0].size
        # Ensure even dimensions for standard video codecs
        even_w = w if w % 2 == 0 else w - 1
        even_h = h if h % 2 == 0 else h - 1

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, float(fps), (even_w, even_h))

        try:
            for f in frames:
                if f.size != (even_w, even_h):
                    f = f.crop((0, 0, even_w, even_h))
                bgr = cv2.cvtColor(np.array(f), cv2.COLOR_RGB2BGR)
                writer.write(bgr)
        finally:
            writer.release()

    @staticmethod
    def _get_default_output_path(fmt: str) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, f"redactsnap_rec_{timestamp}.{fmt}")
