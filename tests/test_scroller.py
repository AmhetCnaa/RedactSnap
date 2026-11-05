"""
Unit tests for the Scrolling Screenshot and Stitching module.
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw

from redactsnap.capture.scroller import ScrollingStitcher


def test_stitching_pair():
    # Create two synthetic frames with a 100px vertical overlap
    w = 400
    h = 300
    overlap = 100

    # Frame 1: Top portion (0 to 300)
    frame1 = Image.new("RGB", (w, h), (240, 240, 240))
    d1 = ImageDraw.Draw(frame1)
    d1.rectangle([50, 50, 150, 80], fill=(255, 0, 0))  # Unique to frame 1
    d1.rectangle([50, 230, 200, 260], fill=(0, 120, 255))  # Located in overlap zone

    # Frame 2: Bottom portion (scrolled down by 200px)
    # The overlap zone from frame 1 is at y=230, which should now appear at y=30 in frame 2
    frame2 = Image.new("RGB", (w, h), (240, 240, 240))
    d2 = ImageDraw.Draw(frame2)
    d2.rectangle([50, 30, 200, 60], fill=(0, 120, 255))  # Matching overlap zone
    d2.rectangle([50, 180, 250, 220], fill=(0, 200, 50))  # Unique to frame 2

    stitched, delta_y, confidence = ScrollingStitcher.stitch_pair(frame1, frame2)

    assert confidence > 0.70
    assert stitched.width == w
    assert stitched.height > h


def test_stitch_sequence():
    f1 = Image.new("RGB", (200, 200), (255, 255, 255))
    f2 = Image.new("RGB", (200, 200), (240, 240, 240))
    f3 = Image.new("RGB", (200, 200), (220, 220, 220))

    result = ScrollingStitcher.stitch_sequence([f1, f2, f3])
    assert result.width == 200
    assert result.height >= 200
