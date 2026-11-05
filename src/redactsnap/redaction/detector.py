"""
Detector module combining OCR spatial coordinates, regex pattern catalog,
and Shannon Entropy analysis to identify exact redaction targets.
"""

from typing import List, Tuple, Optional
from PIL import Image
import numpy as np

from .patterns import PATTERNS, SecretPattern
from .entropy import EntropyAnalyzer
from .ocr.rapid import RapidOCREngine, OCRTextBox


class RedactionTarget:
    """Represents a discovered secret with its type, matched content, and image coordinates."""

    def __init__(
        self,
        name: str,
        category: str,
        matched_text: str,
        bbox: Tuple[int, int, int, int],
        confidence: float
    ):
        self.name = name
        self.category = category
        self.matched_text = matched_text
        self.bbox = bbox  # (x, y, w, h)
        self.confidence = confidence

    def __repr__(self):
        return f"<RedactionTarget {self.name} text='{self.matched_text[:8]}...' bbox={self.bbox}>"


class RedactionDetector:
    """Orchestrates pattern matching and entropy evaluation over OCR results."""

    def __init__(self, ocr_engine: Optional[RapidOCREngine] = None):
        self.ocr_engine = ocr_engine or RapidOCREngine()

    def scan(self, image: Image.Image | np.ndarray) -> Tuple[List[RedactionTarget], List[OCRTextBox]]:
        """
        Scans an image for sensitive tokens.

        Returns:
            Tuple of (redaction_targets, all_ocr_text_boxes)
        """
        ocr_boxes = self.ocr_engine.recognize(image)
        targets: List[RedactionTarget] = []

        for box in ocr_boxes:
            line_text = box.text
            matched_spans: List[Tuple[int, int]] = []

            # 1. Regex Pattern Matching
            for pattern in PATTERNS:
                matches = pattern.find_matches(line_text)
                for start_idx, end_idx, secret_text in matches:
                    sub_box = box.sub_bbox(start_idx, end_idx)
                    targets.append(
                        RedactionTarget(
                            name=pattern.name,
                            category=pattern.category,
                            matched_text=secret_text,
                            bbox=sub_box,
                            confidence=box.confidence
                        )
                    )
                    matched_spans.append((start_idx, end_idx))

            # 2. Shannon Entropy Analysis for Unstructured Secrets
            entropy_matches = EntropyAnalyzer.scan_text(line_text)
            for start_idx, end_idx, token, score, reason in entropy_matches:
                # Skip if already covered by regex
                already_covered = any(
                    (s <= start_idx and end_idx <= e) or (start_idx <= s and e <= end_idx)
                    for s, e in matched_spans
                )
                if already_covered:
                    continue

                sub_box = box.sub_bbox(start_idx, end_idx)
                targets.append(
                    RedactionTarget(
                        name="High-Entropy Secret",
                        category="SECRET",
                        matched_text=token,
                        bbox=sub_box,
                        confidence=box.confidence
                    )
                )

        # Merge overlapping / adjacent bounding boxes
        merged_targets = self._merge_overlapping_targets(targets)
        return merged_targets, ocr_boxes

    @staticmethod
    def _merge_overlapping_targets(targets: List[RedactionTarget]) -> List[RedactionTarget]:
        """Merges targets that overlap spatially within the image."""
        if not targets:
            return []

        # Sort by y, then x
        sorted_targets = sorted(targets, key=lambda t: (t.bbox[1], t.bbox[0]))
        merged = []

        for target in sorted_targets:
            if not merged:
                merged.append(target)
                continue

            last = merged[-1]
            lx, ly, lw, lh = last.bbox
            tx, ty, tw, th = target.bbox

            # Check overlap or tight adjacency
            x_overlap = not (tx > lx + lw or tx + tw < lx)
            y_overlap = not (ty > ly + lh or ty + th < ly)

            if x_overlap and y_overlap:
                # Merge into a single bounding box
                new_x = min(lx, tx)
                new_y = min(ly, ty)
                new_w = max(lx + lw, tx + tw) - new_x
                new_h = max(ly + lh, ty + th) - new_y
                last.bbox = (new_x, new_y, new_w, new_h)
                last.matched_text = f"{last.matched_text} + {target.matched_text}"
            else:
                merged.append(target)

        return merged
