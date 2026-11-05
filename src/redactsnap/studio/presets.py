"""
Gradient presets and styling themes for RedactSnap Social Studio.
Curated color combinations inspired by Raycast, Linear, Apple, and modern dark aesthetics.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass(frozen=True)
class GradientPreset:
    id: str
    name: str
    stops: Tuple[Tuple[int, int, int], ...]
    direction: str = "diagonal_down"  # "diagonal_down", "diagonal_up", "horizontal", "vertical", "radial"
    description: str = ""


PRESETS: List[GradientPreset] = [
    GradientPreset(
        id="obsidian",
        name="Obsidian Dark",
        stops=(
            (9, 13, 22),     # #090D16 - Deep Space
            (24, 32, 47),    # #18202F - Dark Slate
            (15, 23, 42),    # #0F172A - Tailwind Slate 900
            (3, 7, 18),      # #030712 - Charcoal Black
        ),
        direction="diagonal_down",
        description="Linear-style deep stealth dark theme with subtle depth"
    ),
    GradientPreset(
        id="sunset",
        name="Sunset Warmth",
        stops=(
            (74, 0, 224),    # #4A00E0 - Deep Indigo
            (142, 45, 226),  # #8E2DE2 - Royal Purple
            (240, 0, 255),   # #F000FF - Electric Magenta
            (255, 94, 98),   # #FF5E62 - Warm Coral Sunset
        ),
        direction="diagonal_down",
        description="macOS Monterey vibrant dusk gradient"
    ),
    GradientPreset(
        id="emerald",
        name="Emerald Code",
        stops=(
            (6, 78, 59),     # #064E3B - Deep Forest
            (5, 150, 105),   # #059669 - Emerald
            (16, 185, 129),  # #10B981 - Bright Mint
            (6, 182, 212),   # #06B6D4 - Cyan Aqua
        ),
        direction="diagonal_down",
        description="Lush terminal matrix and vibrant mint glow"
    ),
    GradientPreset(
        id="cyber_purple",
        name="Cyber Purple",
        stops=(
            (24, 0, 51),     # #180033 - Deep Midnight
            (67, 56, 202),   # #4338CA - Raycast Indigo
            (124, 58, 237),  # #7C3AED - Electric Violet
            (192, 132, 252), # #C084FC - Soft Lavender
        ),
        direction="diagonal_down",
        description="Raycast-grade futuristic ultraviolet gradient"
    ),
    GradientPreset(
        id="hyper_blue",
        name="Hyper Blue",
        stops=(
            (15, 23, 42),    # #0F172A - Deep Midnight Blue
            (30, 64, 175),   # #1E40AF - Royal Navy
            (59, 130, 246),  # #3B82F6 - Apple Key Blue
            (56, 189, 248),  # #38BDF8 - Sky Cyan
        ),
        direction="diagonal_down",
        description="Apple keynote clean electric ocean blue"
    ),
    GradientPreset(
        id="midnight_gold",
        name="Midnight Amber",
        stops=(
            (17, 24, 39),    # #111827 - Slate Gray
            (120, 53, 15),   # #78350F - Deep Amber
            (217, 119, 6),   # #D97706 - Golden Glow
            (251, 191, 36),  # #FBBF24 - Warm Honey
        ),
        direction="diagonal_down",
        description="Warm luxury titanium and golden ember"
    ),
    GradientPreset(
        id="minimal_dark",
        name="Minimal Clean",
        stops=(
            (24, 24, 27),    # #18181B - Zinc 900
            (39, 39, 42),    # #27272A - Zinc 800
        ),
        direction="vertical",
        description="Subtle monochrome dark background for zero distraction"
    ),
    GradientPreset(
        id="transparent",
        name="Transparent Canvas",
        stops=(
            (0, 0, 0),
            (0, 0, 0),
        ),
        direction="vertical",
        description="Transparent background with floating drop shadow and window frame"
    ),
]


def get_preset_by_id(preset_id: str) -> GradientPreset:
    """Finds a preset by its ID, defaulting to Obsidian Dark."""
    for p in PRESETS:
        if p.id.lower() == preset_id.lower():
            return p
    return PRESETS[0]
