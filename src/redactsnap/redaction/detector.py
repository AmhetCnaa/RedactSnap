"""
Detector module combining OCR spatial coordinates, regex pattern catalog,
and Shannon Entropy analysis to identify exact redaction targets.
Includes rich terminal debug output and contextual Turkish ID handling.
"""

import re
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
        confidence: float,
        matched_texts: Optional[List[str]] = None
    ):
        self.name = name
        self.category = category
        self.matched_text = matched_text
        self.bbox = bbox  # (x, y, w, h)
        self.confidence = confidence
        self.matched_texts: List[str] = list(matched_texts) if matched_texts is not None else [matched_text]

    def __repr__(self):
        return f"<RedactionTarget [{self.category}] {self.name} text='{self.matched_text}' bbox={self.bbox}>"


class RedactionDetector:
    """Orchestrates pattern matching, context analysis, and entropy evaluation over OCR results."""

    def __init__(self, ocr_engine: Optional[RapidOCREngine] = None, debug: bool = True):
        self.ocr_engine = ocr_engine or RapidOCREngine()
        self.debug = debug

    def scan(self, image: Image.Image | np.ndarray) -> Tuple[List[RedactionTarget], List[OCRTextBox]]:
        """
        Scans an image for sensitive tokens with full terminal debug output.
        """
        ocr_boxes = self.ocr_engine.recognize(image)
        targets: List[RedactionTarget] = []

        if self.debug:
            print(f"\n[RedactSnap OCR] Scanned {len(ocr_boxes)} text line(s):")

        for idx, box in enumerate(ocr_boxes):
            line_text = box.text
            matched_spans: List[Tuple[int, int]] = []

            if self.debug:
                print(f"  [#{idx+1}] \"{line_text}\" (conf: {box.confidence:.2f}, bbox: {box.bbox})")

            # 1. Regex Pattern Matching
            for pattern in PATTERNS:
                matches = pattern.find_matches(line_text)
                for start_idx, end_idx, secret_text in matches:
                    sub_box = box.sub_bbox(start_idx, end_idx)
                    target = RedactionTarget(
                        name=pattern.name,
                        category=pattern.category,
                        matched_text=secret_text,
                        bbox=sub_box,
                        confidence=box.confidence
                    )
                    targets.append(target)
                    matched_spans.append((start_idx, end_idx))

                    if self.debug:
                        print(f"      -> [SHIELD] MATCH [{pattern.category}] {pattern.name}: '{secret_text}' (sub-box: {sub_box})")

            # 2. Contextual Fallback for Turkish & Tolerant IDs in lines with keywords or prefixes
            has_id_keyword = bool(
                re.search(
                    r"(?i)(?:\b(?:tc|t\.c\.|kimlik|tckn|tcno|vatanda[sş]l[iı]k|te|tr|id|no)\b|(?:^|[\s:])(?:t|tc|te|tr)[:\s-])",
                    line_text
                )
            )
            if has_id_keyword:
                # Find any 10 or 11 digit sequence in this line (with optional spaces/dashes)
                for m in re.finditer(r"(?<![0-9])([0-9](?:[\s.-]*[0-9]){9,10})(?![0-9])", line_text):
                    s_idx, e_idx = m.start(1), m.end(1)
                    already_covered = any(s <= s_idx and e_idx <= e for s, e in matched_spans)
                    if not already_covered:
                        sub_box = box.sub_bbox(s_idx, e_idx)
                        target = RedactionTarget(
                            name="Contextual Turkish ID / Tolerant ID",
                            category="PII",
                            matched_text=m.group(1),
                            bbox=sub_box,
                            confidence=box.confidence
                        )
                        targets.append(target)
                        matched_spans.append((s_idx, e_idx))
                        if self.debug:
                            print(f"      -> [SHIELD] CONTEXT MATCH [PII] Contextual ID: '{m.group(1)}' (sub-box: {sub_box})")

            # 3. Shannon Entropy Analysis for Unstructured Secrets
            entropy_matches = EntropyAnalyzer.scan_text(line_text)
            for start_idx, end_idx, token, score, reason in entropy_matches:
                already_covered = any(
                    (s <= start_idx and end_idx <= e) or (start_idx <= s and e <= end_idx)
                    for s, e in matched_spans
                )
                if already_covered:
                    continue

                sub_box = box.sub_bbox(start_idx, end_idx)
                target = RedactionTarget(
                    name="High-Entropy Secret",
                    category="SECRET",
                    matched_text=token,
                    bbox=sub_box,
                    confidence=box.confidence
                )
                targets.append(target)

                if self.debug:
                    print(f"      -> [SHIELD] ENTROPY MATCH [SECRET] '{token}' (H={score:.2f}, {reason})")

        merged_targets = self._merge_overlapping_targets(targets)

        if self.debug:
            if merged_targets:
                print(f"[RedactSnap] [SHIELD] Total redacted secret(s): {len(merged_targets)}\n")
            else:
                print("[RedactSnap] Clean! No secrets detected.\n")

        return merged_targets, ocr_boxes

    @staticmethod
    def _boxes_overlap(b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int], tol_y: int = 2) -> bool:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        x_overlap = not (x2 > x1 + w1 or x2 + w2 < x1)
        y_overlap = not (y2 > y1 + h1 + tol_y or y2 + h2 < y1 - tol_y)
        return x_overlap and y_overlap

    @classmethod
    def _merge_two_targets(cls, t1: RedactionTarget, t2: RedactionTarget) -> RedactionTarget:
        x1, y1, w1, h1 = t1.bbox
        x2, y2, w2, h2 = t2.bbox
        new_x = min(x1, x2)
        new_y = min(y1, y2)
        new_w = max(x1 + w1, x2 + w2) - new_x
        new_h = max(y1 + h1, y2 + h2) - new_y

        merged_texts = list(t1.matched_texts)
        for txt in t2.matched_texts:
            if txt not in merged_texts:
                merged_texts.append(txt)

        combo_text = t1.matched_text
        if t2.matched_text not in t1.matched_text:
            combo_text = f"{t1.matched_text} + {t2.matched_text}"

        return RedactionTarget(
            name=t1.name,
            category=t1.category,
            matched_text=combo_text,
            bbox=(new_x, new_y, new_w, new_h),
            confidence=max(t1.confidence, t2.confidence),
            matched_texts=merged_texts
        )

    @classmethod
    def _merge_overlapping_targets(cls, targets: List[RedactionTarget]) -> List[RedactionTarget]:
        """Iteratively merges targets that overlap spatially within the image across all candidates."""
        if not targets:
            return []

        current = list(targets)
        changed = True
        while changed:
            changed = False
            merged: List[RedactionTarget] = []
            used = [False] * len(current)

            for i in range(len(current)):
                if used[i]:
                    continue
                ti = current[i]
                for j in range(i + 1, len(current)):
                    if used[j]:
                        continue
                    tj = current[j]
                    if cls._boxes_overlap(ti.bbox, tj.bbox):
                        ti = cls._merge_two_targets(ti, tj)
                        used[j] = True
                        changed = True
                merged.append(ti)
                used[i] = True
            current = merged

        return current
