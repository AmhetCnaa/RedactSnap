"""
Social Studio Beautifier Canvas for RedactSnap.
Transforms raw screenshots into Apple / Linear / Raycast grade visuals with:
- Multi-stop smooth gradient backgrounds
- Multi-layer diffuse soft drop shadows
- macOS traffic-light window chrome
- Anti-aliased rounded corners and subtle inner borders
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .presets import GradientPreset, PRESETS, get_preset_by_id


@dataclass
class StudioConfig:
    """Configuration options for the Studio Beautifier engine."""
    preset: GradientPreset = PRESETS[0]  # Obsidian Dark by default
    padding: int = 48                    # 16, 32, 48, 64, 96 px
    corner_radius: int = 14              # Corner radius of the captured window
    show_window_chrome: bool = True      # macOS traffic light title bar
    window_title: str = ""               # Centered window title (optional)
    shadow_intensity: float = 1.0        # Multiplier for shadow depth
    inner_border: bool = True            # 1px subtle highlight border


class StudioBeautifier:
    """Renders social-media-ready framed captures."""

    @classmethod
    def render(cls, image: Image.Image, config: Optional[StudioConfig] = None) -> Image.Image:
        """
        Takes a screenshot image and renders it on a beautified canvas.
        """
        if config is None:
            config = StudioConfig()

        # Ensure image is in RGBA
        content = image.convert("RGBA")

        # 1. Build the Window (Optionally add title bar, round corners, add inner border)
        window_img = cls._build_window(content, config)
        win_w, win_h = window_img.size

        # 2. Determine Canvas Dimensions
        canvas_w = win_w + (config.padding * 2)
        canvas_h = win_h + (config.padding * 2)

        # 3. Generate Multi-Layer Diffuse Shadow
        shadow_canvas = cls._generate_shadow_canvas(
            window_img=window_img,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            padding=config.padding,
            intensity=config.shadow_intensity
        )

        # 4. Generate Background (Gradient or Transparent)
        if config.preset.id == "transparent":
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        else:
            canvas = cls._generate_gradient(canvas_w, canvas_h, config.preset)

        # 5. Composite: Background -> Shadow -> Window
        canvas = Image.alpha_composite(canvas, shadow_canvas)

        # Position window centered in padding
        window_x = config.padding
        window_y = config.padding
        canvas.paste(window_img, (window_x, window_y), mask=window_img)

        return canvas

    @classmethod
    def _build_window(cls, content: Image.Image, config: StudioConfig) -> Image.Image:
        """Adds optional macOS title bar, rounds corners, and applies inner stroke."""
        w, h = content.size
        title_bar_h = 36 if config.show_window_chrome else 0

        total_h = h + title_bar_h
        window = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))

        # 1. Render Title Bar if enabled
        if config.show_window_chrome:
            title_bar = Image.new("RGBA", (w, title_bar_h), (18, 24, 33, 255))
            draw_tb = ImageDraw.Draw(title_bar)

            # Draw bottom border of title bar
            draw_tb.line([(0, title_bar_h - 1), (w, title_bar_h - 1)], fill=(255, 255, 255, 20), width=1)

            # Draw Traffic Light Dots (Close, Minimize, Expand)
            dot_diameter = 12
            dot_y = (title_bar_h - dot_diameter) // 2
            start_x = 16
            spacing = 20

            dots = [
                ((255, 95, 86), (224, 68, 62)),   # Red (#FF5F56)
                ((255, 189, 46), (222, 161, 35)), # Yellow (#FFBD2E)
                ((39, 201, 63), (26, 171, 47)),   # Green (#27C93F)
            ]

            for i, (fill_col, stroke_col) in enumerate(dots):
                dx = start_x + (i * spacing)
                draw_tb.ellipse(
                    [dx, dot_y, dx + dot_diameter, dot_y + dot_diameter],
                    fill=fill_col + (255,),
                    outline=stroke_col + (255,),
                    width=1
                )

            # Optional Window Title
            if config.window_title:
                font = ImageFont.load_default()
                draw_tb.text(
                    (w // 2, title_bar_h // 2),
                    config.window_title,
                    fill=(226, 232, 240, 180),
                    anchor="mm",
                    font=font
                )

            window.paste(title_bar, (0, 0))

        # 2. Paste Content below title bar
        window.paste(content, (0, title_bar_h))

        # 3. Apply Anti-Aliased Rounded Corners Mask
        mask = Image.new("L", (w, total_h), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle(
            [0, 0, w, total_h],
            radius=config.corner_radius,
            fill=255
        )

        window.putalpha(mask)

        # 4. Draw 1px subtle inner border
        if config.inner_border:
            border_layer = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(border_layer)
            draw_border.rounded_rectangle(
                [0, 0, w - 1, total_h - 1],
                radius=config.corner_radius,
                outline=(255, 255, 255, 35),
                width=1
            )
            window = Image.alpha_composite(window, border_layer)

        return window

    @classmethod
    def _generate_shadow_canvas(
        cls,
        window_img: Image.Image,
        canvas_w: int,
        canvas_h: int,
        padding: int,
        intensity: float
    ) -> Image.Image:
        """
        Creates a photorealistic 3-tier diffuse drop shadow.
        Tier 1: Ambient Contact Shadow (tight, medium opacity)
        Tier 2: Primary Diffuse Shadow (broad, soft)
        Tier 3: Ambient Floor Spread (subtle deep glow)
        """
        if intensity <= 0.0:
            return Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # Extract window silhouette alpha channel
        win_w, win_h = window_img.size
        alpha_mask = window_img.split()[3]

        # Base black silhouette
        silhouette = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 255))
        silhouette.putalpha(alpha_mask)

        shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # Tier definitions: (offset_x, offset_y, blur_radius, alpha_multiplier)
        tiers = [
            (0, 4, 12, 0.35 * intensity),   # Contact shadow
            (0, 20, 36, 0.25 * intensity),  # Primary diffuse
            (0, 44, 72, 0.15 * intensity),  # Floor spread
        ]

        for off_x, off_y, blur_r, alpha_scale in tiers:
            tier_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            paste_x = padding + off_x
            paste_y = padding + off_y

            # Place silhouette onto canvas with offset
            tier_canvas.paste(silhouette, (paste_x, paste_y), mask=silhouette)

            # Blur
            blurred = tier_canvas.filter(ImageFilter.GaussianBlur(blur_r))

            # Scale alpha
            if alpha_scale < 1.0:
                r, g, b, a = blurred.split()
                a_arr = np.array(a, dtype=np.float32) * alpha_scale
                a = Image.fromarray(a_arr.clip(0, 255).astype(np.uint8), mode="L")
                blurred.putalpha(a)

            shadow_canvas = Image.alpha_composite(shadow_canvas, blurred)

        return shadow_canvas

    @classmethod
    def _generate_gradient(cls, width: int, height: int, preset: GradientPreset) -> Image.Image:
        """
        Generates a high-precision multi-stop gradient background using NumPy.
        """
        stops = preset.stops
        num_stops = len(stops)

        # Coordinate grid normalized 0.0 to 1.0
        x = np.linspace(0.0, 1.0, width, dtype=np.float32)
        y = np.linspace(0.0, 1.0, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        if preset.direction == "diagonal_down":
            t = (xx + yy) / 2.0
        elif preset.direction == "diagonal_up":
            t = (xx + (1.0 - yy)) / 2.0
        elif preset.direction == "horizontal":
            t = xx
        elif preset.direction == "vertical":
            t = yy
        elif preset.direction == "radial":
            t = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.707
        else:
            t = (xx + yy) / 2.0

        t = np.clip(t, 0.0, 1.0)

        # Interpolate across stops
        stop_positions = np.linspace(0.0, 1.0, num_stops, dtype=np.float32)
        colors_arr = np.array(stops, dtype=np.float32)

        r_channel = np.interp(t, stop_positions, colors_arr[:, 0])
        g_channel = np.interp(t, stop_positions, colors_arr[:, 1])
        b_channel = np.interp(t, stop_positions, colors_arr[:, 2])

        rgb = np.stack([r_channel, g_channel, b_channel], axis=-1).astype(np.uint8)
        grad_img = Image.fromarray(rgb, mode="RGB")
        return grad_img.convert("RGBA")
