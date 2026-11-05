"""
RapidOCR wrapper for local, offline ONNX-powered optical character recognition.
Extracts line/word bounding boxes and text without any external binary dependencies.
"""

from typing import List, Tuple, Optional
import numpy as np
from PIL import Image, ImageEnhance

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
        Runs offline OCR on the given PIL Image or NumPy array with intelligent
        preprocessing (LANCZOS upscaling + contrast/sharpness enhancement)
        to reliably detect small fonts in browser address bars, forms, and code editors.
        """
        if not self.is_available:
            return []

        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image).convert("RGB")
        else:
            pil_img = image.convert("RGB")

        orig_w, orig_h = pil_img.size

        # Adaptive scaling: small crops (e.g. search bars, single text lines)
        # benefit dramatically from 2.0x LANCZOS upscaling and edge sharpening.
        # Large images (> 1600px) are kept at 1.0x to conserve RAM and speed.
        if max(orig_w, orig_h) <= 1600:
            scale_factor = 2.0
        else:
            scale_factor = 1.0

        if scale_factor != 1.0:
            new_w = int(orig_w * scale_factor)
            new_h = int(orig_h * scale_factor)
            processed_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            processed_img = pil_img

        # Enhance contrast and sharpness for subtle grey UI text (e.g., Chrome/Brave URL bar)
        contrast_enhancer = ImageEnhance.Contrast(processed_img)
        processed_img = contrast_enhancer.enhance(1.35)
        sharpness_enhancer = ImageEnhance.Sharpness(processed_img)
        processed_img = sharpness_enhancer.enhance(1.4)

        arr = np.array(processed_img)
        raw_results, _ = self._engine(arr)
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
