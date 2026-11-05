"""
Main redaction pipeline orchestrating OCR, detection, and aesthetic masking.
"""

from typing import List, Tuple, Optional
from PIL import Image
import numpy as np

from .detector import RedactionDetector, RedactionTarget
from .masker import RedactionMasker, RedactionStyle
from .ocr.rapid import RapidOCREngine, OCRTextBox


class RedactionPipeline:
    """
    High-level API for running offline privacy scanning and visual redaction.
    """

    def __init__(
        self,
        ocr_engine: Optional[RapidOCREngine] = None,
        detector: Optional[RedactionDetector] = None
    ):
        self.ocr_engine = ocr_engine or RapidOCREngine()
        self.detector = detector or RedactionDetector(self.ocr_engine)

    def process(
        self,
        image: Image.Image,
        style: RedactionStyle = RedactionStyle.GAUSSIAN_BLUR
    ) -> Tuple[Image.Image, List[RedactionTarget]]:
        """
        Scans image for sensitive data and returns the redacted image along with
        a list of discovered redaction targets.

        Returns:
            Tuple of (redacted_image, targets)
        """
        targets, _ = self.detector.scan(image)
        bboxes = [t.bbox for t in targets]

        redacted_img = RedactionMasker.apply_redaction(
            image=image,
            bboxes=bboxes,
            style=style
        )
        return redacted_img, targets

    def copy_as_text(self, image: Image.Image, redact_secrets: bool = False) -> str:
        """
        Extracts all recognized text from image.
        If redact_secrets is True, replaces matched secrets with [REDACTED].
        """
        if not redact_secrets:
            return self.ocr_engine.extract_full_text(image)

        targets, ocr_boxes = self.detector.scan(image)
        if not targets:
            return "\n".join(b.text for b in ocr_boxes)

        lines = []
        for box in ocr_boxes:
            line_str = box.text
            for target in targets:
                for sub_secret in target.matched_texts:
                    if sub_secret and sub_secret in line_str:
                        line_str = line_str.replace(sub_secret, "[REDACTED]")
            lines.append(line_str)

        return "\n".join(lines)
