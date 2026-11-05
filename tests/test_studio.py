"""
Unit tests for the Studio Beautifier canvas module.
"""

import pytest
from PIL import Image

from redactsnap.studio.presets import PRESETS, get_preset_by_id
from redactsnap.studio.beautifier import StudioBeautifier, StudioConfig


def test_presets_catalog():
    assert len(PRESETS) >= 6
    obsidian = get_preset_by_id("obsidian")
    assert obsidian.id == "obsidian"
    assert len(obsidian.stops) >= 2

    sunset = get_preset_by_id("sunset")
    assert sunset.id == "sunset"


def test_beautifier_render_dimensions():
    # Content image: 400x300
    content = Image.new("RGB", (400, 300), color=(30, 41, 59))

    config = StudioConfig(
        padding=48,
        show_window_chrome=True,  # adds 36px title bar
        corner_radius=12
    )

    result = StudioBeautifier.render(content, config)

    # Window height = 300 + 36 = 336
    # Total canvas width = 400 + 48*2 = 496
    # Total canvas height = 336 + 48*2 = 432
    assert result.size == (496, 432)
    assert result.mode == "RGBA"


def test_beautifier_without_chrome():
    content = Image.new("RGB", (200, 200), color=(255, 255, 255))
    config = StudioConfig(
        padding=32,
        show_window_chrome=False
    )
    result = StudioBeautifier.render(content, config)
    assert result.size == (264, 264)


def test_all_presets_render():
    content = Image.new("RGB", (100, 100), color=(10, 10, 10))
    for preset in PRESETS:
        config = StudioConfig(preset=preset, padding=16)
        res = StudioBeautifier.render(content, config)
        assert res.size == (132, 168)  # 100 + 32, 100 + 36 + 32


def test_transparent_preset():
    content = Image.new("RGB", (150, 150), color=(20, 20, 20))
    # Without shadow, alpha should be strictly 0
    config_no_shadow = StudioConfig(preset=get_preset_by_id("transparent"), padding=32, shadow_intensity=0.0)
    res_no_shadow = StudioBeautifier.render(content, config_no_shadow)
    assert res_no_shadow.getpixel((0, 0))[3] == 0

    # With shadow, corner has soft translucent shadow tail
    config_shadow = StudioConfig(preset=get_preset_by_id("transparent"), padding=32)
    res_shadow = StudioBeautifier.render(content, config_shadow)
    assert res_shadow.getpixel((0, 0))[3] < 20
