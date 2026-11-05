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
        confidence: float
    ):
        self.name = name
        self.category = category
        self.matched_text = matched_text
        self.bbox = bbox  # (x, y, w, h)
        self.confidence = confidence

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
    def _merge_overlapping_targets(targets: List[RedactionTarget]) -> List[RedactionTarget]:
        """Merges targets that overlap spatially within the image."""
        if not targets:
            return []

        sorted_targets = sorted(targets, key=lambda t: (t.bbox[1], t.bbox[0]))
        merged = []

        for target in sorted_targets:
            if not merged:
                merged.append(target)
                continue

            last = merged[-1]
            lx, ly, lw, lh = last.bbox
            tx, ty, tw, th = target.bbox

            x_overlap = not (tx > lx + lw or tx + tw < lx)
            y_overlap = not (ty > ly + lh or ty + th < ly)

            if x_overlap and y_overlap:
                new_x = min(lx, tx)
                new_y = min(ly, ty)
                new_w = max(lx + lw, tx + tw) - new_x
                new_h = max(ly + lh, ty + th) - new_y
                last.bbox = (new_x, new_y, new_w, new_h)
                last.matched_text = f"{last.matched_text} + {target.matched_text}"
            else:
                merged.append(target)

        return merged
