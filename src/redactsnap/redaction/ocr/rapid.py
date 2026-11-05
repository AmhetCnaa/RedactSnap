"""
RapidOCR wrapper for local, offline ONNX-powered optical character recognition.
Extracts line/word bounding boxes and text without any external binary dependencies.
"""

from typing import List, Tuple, Optional
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
    """Singleton wrapper for RapidOCR ONNX inference engine."""

    _instance: Optional["RapidOCREngine"] = None
    _engine: Optional[RapidOCR] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if RapidOCR is not None:
                cls._engine = RapidOCR()
        return cls._instance

    @property
    def is_available(self) -> bool:
        return self._engine is not None

    def recognize(self, image: Image.Image | np.ndarray) -> List[OCRTextBox]:
        """
        Runs offline OCR on the given PIL Image or NumPy array.
        Returns a list of OCRTextBox instances.
        """
        if not self.is_available:
            return []

        if isinstance(image, Image.Image):
            arr = np.array(image.convert("RGB"))
        else:
            arr = image

        raw_results, _ = self._engine(arr)
        if not raw_results:
            return []

        boxes = []
        for item in raw_results:
            # item format: [polygon_points, text, confidence]
            poly, text, score = item[0], item[1], float(item[2])
            boxes.append(OCRTextBox(text=text, confidence=score, polygon=poly))

        return boxes

    def extract_full_text(self, image: Image.Image | np.ndarray) -> str:
        """Extracts complete text content as a formatted string (for 1-click clipboard copy)."""
        boxes = self.recognize(image)
        return "\n".join(box.text for box in boxes)
