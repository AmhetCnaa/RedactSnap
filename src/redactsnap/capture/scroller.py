"""
Vertical Scrolling Screenshot and Stitching Engine for RedactSnap.
Captures long web pages, code editors, and documents by combining consecutive frames
using OpenCV vertical cross-correlation template matching.
"""

import time
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np
import cv2

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QGuiApplication
from pynput.mouse import Controller as MouseController

from .grabber import ScreenGrabber


class ScrollingStitcher:
    """
    Computes vertical pixel overlap between consecutive scrolling frames
    and seamlessly stitches them into a single continuous tall image.
    """

    @classmethod
    def stitch_pair(
        cls,
        top_img: Image.Image,
        bottom_img: Image.Image,
        min_confidence: float = 0.65
    ) -> Tuple[Image.Image, int, float]:
        """
        Stitches two consecutive vertically overlapping frames.

        Returns:
            Tuple of (stitched_image, offset_dy, confidence_score)
        """
        top_w, top_h = top_img.size
        bot_w, bot_h = bottom_img.size

        # Align widths if slight difference
        common_w = min(top_w, bot_w)
        if top_w != common_w:
            top_img = top_img.crop((0, 0, common_w, top_h))
        if bot_w != common_w:
            bottom_img = bottom_img.crop((0, 0, common_w, bot_h))

        top_arr = np.array(top_img.convert("RGB"))
        bot_arr = np.array(bottom_img.convert("RGB"))

        # Convert to grayscale for robust feature matching
        top_gray = cv2.cvtColor(top_arr, cv2.COLOR_RGB2GRAY)
        bot_gray = cv2.cvtColor(bot_arr, cv2.COLOR_RGB2GRAY)

        # Extract a template strip from the lower region of top image
        strip_h = min(120, max(30, top_h // 4))
        strip_y_start = top_h - strip_h - min(10, top_h // 10)
        strip = top_gray[strip_y_start : strip_y_start + strip_h, :]

        # Search for this strip in the upper 85% of the bottom image
        search_region_h = int(bot_h * 0.85)
        search_region = bot_gray[:search_region_h, :]

        res = cv2.matchTemplate(search_region, strip, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        match_y = max_loc[1]
        confidence = float(max_val)

        # If confidence is below threshold, simple fallback stack
        if confidence < min_confidence:
            # Fallback: append bottom directly
            stitched = Image.new("RGBA", (common_w, top_h + bot_h))
            stitched.paste(top_img, (0, 0))
            stitched.paste(bottom_img, (0, top_h))
            return stitched, bot_h, confidence

        # Calculate where new unique content begins in bottom image
        unique_start_y = match_y + strip_h
        unique_bottom = bottom_img.crop((0, unique_start_y, common_w, bot_h))

        # Composite stitched image
        total_h = top_h + unique_bottom.height
        stitched = Image.new("RGBA", (common_w, total_h))
        stitched.paste(top_img, (0, 0))
        stitched.paste(unique_bottom, (0, top_h))

        delta_y = unique_bottom.height
        return stitched, delta_y, confidence

    @classmethod
    def stitch_sequence(cls, frames: List[Image.Image]) -> Image.Image:
        """
        Sequentially stitches an ordered list of scrolling frames.
        """
        if not frames:
            return Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        if len(frames) == 1:
            return frames[0].copy()

        current = frames[0]
        for next_frame in frames[1:]:
            stitched, _, _ = cls.stitch_pair(current, next_frame)
            current = stitched

        return current


class ScrollingCaptureSession:
    """
    Automates scrolling capture by sending wheel scroll events to the target window,
    buffering screenshots, and stitching them into a tall panoramic image.
    """

    @classmethod
    def capture_and_stitch(
        cls,
        target_rect: QRect,
        steps: int = 4,
        scroll_delta: int = -4,
        pause_sec: float = 0.35
    ) -> Image.Image:
        """
        Captures successive scrolling screenshots and stitches them.
        """
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return Image.new("RGBA", (100, 100))

        mouse = MouseController()
        # Position mouse in center of target rect
        cx = target_rect.x() + target_rect.width() // 2
        cy = target_rect.y() + target_rect.height() // 2
        mouse.position = (cx, cy)

        frames: List[Image.Image] = []

        for step in range(steps):
            # 1. Grab current view
            pix = screen.grabWindow(
                0,
                target_rect.x(),
                target_rect.y(),
                target_rect.width(),
                target_rect.height()
            )
            pil_img = ScreenGrabber.pixmap_to_pil(pix).convert("RGBA")
            frames.append(pil_img)

            if step < steps - 1:
                # 2. Scroll down
                mouse.scroll(0, scroll_delta)
                time.sleep(pause_sec)

        # 3. Stitch all frames
        return ScrollingStitcher.stitch_sequence(frames)
