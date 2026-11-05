"""
Capture module for RedactSnap.
"""

from .grabber import ScreenGrabber
from .overlay import SnippingOverlay, OverlayState
from .recorder import ScreenRecorder
from .scroller import ScrollingStitcher, ScrollingCaptureSession

__all__ = [
    "ScreenGrabber",
    "SnippingOverlay",
    "OverlayState",
    "ScreenRecorder",
    "ScrollingStitcher",
    "ScrollingCaptureSession",
]
