"""
Aesthetic masking engine for RedactSnap.
Applies Gaussian Blur with smooth edge feathering, modern dark pills, or mosaic pixelation.
"""

from enum import Enum
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


class RedactionStyle(Enum):
    GAUSSIAN_BLUR = "gaussian_blur"
    DARK_PILL = "dark_pill"
    PIXELATE = "pixelate"
    BLACK_BAR = "black_bar"


class RedactionMasker:
    """Applies visual censorship effects over detected bounding boxes."""

    @classmethod
    def apply_redaction(
        cls,
        image: Image.Image,
        bboxes: List[Tuple[int, int, int, int]],
        style: RedactionStyle = RedactionStyle.GAUSSIAN_BLUR
    ) -> Image.Image:
        """
        Applies redactions to an image given bounding boxes [(x, y, w, h), ...].
        """
        if not bboxes:
            return image.copy()

        if style == RedactionStyle.GAUSSIAN_BLUR:
            return cls._apply_feathered_gaussian_blur(image, bboxes)
        elif style == RedactionStyle.DARK_PILL:
            return cls._apply_dark_pill(image, bboxes)
        elif style == RedactionStyle.PIXELATE:
            return cls._apply_pixelation(image, bboxes)
        elif style == RedactionStyle.BLACK_BAR:
            return cls._apply_black_bar(image, bboxes)

        return image.copy()

    @classmethod
    def _apply_feathered_gaussian_blur(
        cls,
        image: Image.Image,
        bboxes: List[Tuple[int, int, int, int]]
    ) -> Image.Image:
        """Applies Gaussian blur with smooth feathered edges for clean aesthetics."""
        img_arr = np.array(image.convert("RGBA"))
        h_img, w_img = img_arr.shape[:2]

        for x, y, w, h in bboxes:
            # Clamp inside image bounds
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(w_img, x + w)
            y2 = min(h_img, y + h)

            if x2 <= x1 or y2 <= y1:
                continue

            roi = img_arr[y1:y2, x1:x2]

            # Determine kernel size based on ROI height
            k_size = max(15, (h // 2) * 2 + 1)
            # Ensure odd
            if k_size % 2 == 0:
                k_size += 1

            # Heavy blur
            blurred_roi = cv2.GaussianBlur(roi, (k_size, k_size), sigmaX=k_size / 2)

            # Feathering mask (smooth transition on outer 3 pixels)
            mask = np.ones((y2 - y1, x2 - x1), dtype=np.float32)
            feather_px = min(4, (y2 - y1) // 3, (x2 - x1) // 3)

            if feather_px > 0:
                for i in range(feather_px):
                    alpha = (i + 1) / (feather_px + 1)
                    mask[i, :] *= alpha
                    mask[-(i + 1), :] *= alpha
                    mask[:, i] *= alpha
                    mask[:, -(i + 1)] *= alpha

            # Alpha blend blurred ROI into original ROI
            for c in range(4):
                roi[:, :, c] = (
                    roi[:, :, c] * (1.0 - mask) + blurred_roi[:, :, c] * mask
                ).astype(np.uint8)

            img_arr[y1:y2, x1:x2] = roi

        return Image.fromarray(img_arr, mode="RGBA")

    @classmethod
    def _apply_dark_pill(
        cls,
        image: Image.Image,
        bboxes: List[Tuple[int, int, int, int]]
    ) -> Image.Image:
        """Draws modern, sleek dark slate pills with rounded corners."""
        res = image.convert("RGBA")
        draw = ImageDraw.Draw(res)

        for x, y, w, h in bboxes:
            radius = min(h // 2, 8)
            # Modern Tailwind Slate 900
            fill_color = (15, 23, 42, 245)
            border_color = (255, 255, 255, 45)

            draw.rounded_rectangle(
                [x, y, x + w, y + h],
                radius=radius,
                fill=fill_color,
                outline=border_color,
                width=1
            )

        return res

    @classmethod
    def _apply_pixelation(
        cls,
        image: Image.Image,
        bboxes: List[Tuple[int, int, int, int]],
        pixel_size: int = 8
    ) -> Image.Image:
        """Applies retro mosaic pixelation."""
        img_arr = np.array(image.convert("RGBA"))
        h_img, w_img = img_arr.shape[:2]

        for x, y, w, h in bboxes:
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)

            if x2 <= x1 or y2 <= y1:
                continue

            roi = img_arr[y1:y2, x1:x2]
            rw, rh = roi.shape[1], roi.shape[0]

            small_w = max(1, rw // pixel_size)
            small_h = max(1, rh // pixel_size)

            small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)

            img_arr[y1:y2, x1:x2] = pixelated

        return Image.fromarray(img_arr, mode="RGBA")

    @classmethod
    def _apply_black_bar(
        cls,
        image: Image.Image,
        bboxes: List[Tuple[int, int, int, int]]
    ) -> Image.Image:
        """Draws classic solid black bars."""
        res = image.convert("RGBA")
        draw = ImageDraw.Draw(res)
        for x, y, w, h in bboxes:
            draw.rectangle([x, y, x + w, y + h], fill=(0, 0, 0, 255))
        return res
