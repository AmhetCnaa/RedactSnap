"""
RapidOCR wrapper for local, offline ONNX-powered optical character recognition.
Extracts line/word bounding boxes and text without any external binary dependencies.
"""

import threading
from typing import List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None


class OCRTextBox:
    """Represents a recognized text segment with its spatial bounding box and polygon."""

    def __init__(self, text: str, confidence: float, polygon: List[List[float]]):
        self.text = text
        self.confidence = confidence
        self.polygon = polygon

        # Calculate bounding box (x, y, w, h)
        xs = [pt[0] for pt in polygon]
        ys = [pt[1] for pt in polygon]
        self.x = int(round(min(xs)))
        self.y = int(round(min(ys)))
        self.w = int(round(max(xs) - min(xs)))
        self.h = int(round(max(ys) - min(ys)))

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def sub_bbox(self, start_char_idx: int, end_char_idx: int, padding_px: int = 4) -> Tuple[int, int, int, int]:
        """
        Calculates an interpolated sub-bounding box for a matched secret
        within this text box, with safety padding.
        """
        total_len = max(len(self.text), 1)
        start_ratio = max(0.0, min(1.0, start_char_idx / total_len))
        end_ratio = max(0.0, min(1.0, end_char_idx / total_len))

        sub_x = int(round(self.x + start_ratio * self.w)) - padding_px
        sub_w = int(round((end_ratio - start_ratio) * self.w)) + (padding_px * 2)
        sub_y = self.y - padding_px
        sub_h = self.h + (padding_px * 2)

        return (max(0, sub_x), max(0, sub_y), max(1, sub_w), max(1, sub_h))


class RapidOCREngine:
    """Singleton wrapper for RapidOCR ONNX inference engine with warmup and fast preprocessing."""

    _instance: Optional["RapidOCREngine"] = None
    _engine: Optional[RapidOCR] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._engine = None
        return cls._instance

    @classmethod
    def _ensure_initialized(cls) -> Optional[RapidOCR]:
        """Lazily initializes the RapidOCR ONNX models under lock in a background thread."""
        with cls._lock:
            if cls._engine is None and RapidOCR is not None:
                try:
                    cls._engine = RapidOCR()
                except Exception:
                    cls._engine = None
            return cls._engine

    @property
    def is_available(self) -> bool:
        if RapidOCR is None:
            return False
        if self._engine is not None:
            return True
        return RapidOCR is not None

    def warmup(self):
        """Pre-warms the ONNX runtime session to avoid cold-start lag."""
        engine = self._ensure_initialized()
        if engine is not None:
            with self._lock:
                try:
                    dummy = np.zeros((32, 32, 3), dtype=np.uint8)
                    engine(dummy)
                except Exception:
                    pass

    def recognize(self, image: Image.Image | np.ndarray) -> List[OCRTextBox]:
        """
        Runs offline OCR on the given PIL Image or NumPy array with hyper-fast
        adaptive preprocessing (OpenCV Bilinear scaling + contrast enhancement)
        optimizing both latency and recognition accuracy on small UI fonts.
        """
        engine = self._ensure_initialized()
        if engine is None:
            return []

        if isinstance(image, np.ndarray):
            arr = image.copy()
            if len(arr.shape) == 2:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
            elif arr.shape[2] == 4:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        else:
            arr = np.array(image.convert("RGB"))

        orig_h, orig_w = arr.shape[:2]

        # Fast adaptive scaling:
        # Scale only small single-line crops (e.g. search bars, small buttons where h < 80 or w < 300)
        # by 1.35x (max 1.5x) using fast SIMD cv2.INTER_LINEAR interpolation.
        # Normal & large captures (h >= 80) run at 1.0x native resolution with 0 resize overhead.
        if orig_h < 80 or orig_w < 300:
            scale_factor = 1.35
            new_w = int(orig_w * scale_factor)
            new_h = int(orig_h * scale_factor)
            processed_arr = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            scale_factor = 1.0
            processed_arr = arr

        # Fast contrast adjustment via OpenCV scaling (alpha=1.2, beta=-5)
        # Keeps character edges crisp for low-contrast grey text in browser URL bars
        processed_arr = cv2.convertScaleAbs(processed_arr, alpha=1.2, beta=-5)

        with self._lock:
            raw_results, _ = engine(processed_arr)
        if not raw_results:
            return []

        boxes = []
        for item in raw_results:
            # item format: [polygon_points, text, confidence]
            poly, text, score = item[0], item[1], float(item[2])
            if scale_factor != 1.0:
                poly = [[pt[0] / scale_factor, pt[1] / scale_factor] for pt in poly]
            boxes.append(OCRTextBox(text=text, confidence=score, polygon=poly))

        return boxes

    def extract_full_text(self, image: Image.Image | np.ndarray) -> str:
        """Extracts complete text content as a formatted string (for 1-click clipboard copy)."""
        boxes = self.recognize(image)
        return "\n".join(box.text for box in boxes)
