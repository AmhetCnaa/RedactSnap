"""
Studio Beautifier module for RedactSnap.
"""

from .presets import GradientPreset, PRESETS, get_preset_by_id
from .beautifier import StudioBeautifier, StudioConfig
from .annotations import Annotation, AnnotationType, AnnotationRenderer

__all__ = [
    "GradientPreset",
    "PRESETS",
    "get_preset_by_id",
    "StudioBeautifier",
    "StudioConfig",
    "Annotation",
    "AnnotationType",
    "AnnotationRenderer",
]
