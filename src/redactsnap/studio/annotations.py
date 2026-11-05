"""
Smart Annotation and Drawing Engine for RedactSnap.
Provides vector arrows, auto-incrementing step numbers, spotlights,
highlighters, and shapes with dual PIL and QPainter rendering pipelines.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from PyQt6.QtCore import QPointF, QRectF, Qt


class AnnotationType(Enum):
    STEP_NUMBER = "step_number"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    HIGHLIGHTER = "highlighter"
    SPOTLIGHT = "spotlight"


@dataclass
class Annotation:
    """Represents a vector annotation item."""
    type: AnnotationType
    start_pos: Tuple[int, int]
    end_pos: Tuple[int, int]
    color: Tuple[int, int, int, int] = (255, 59, 48, 255)  # Apple Red by default
    stroke_width: int = 3
    text: str = ""
    radius: int = 14


class AnnotationRenderer:
    """
    Renders annotations onto PIL Images for saving/clipboard,
    and provides QPainter rendering for smooth 60 FPS interactive preview.
    """

    @classmethod
    def render_on_image(cls, image: Image.Image, annotations: List[Annotation]) -> Image.Image:
        """Draws all annotations on top of a PIL Image."""
        if not annotations:
            return image.copy()

        canvas = image.convert("RGBA")

        # 1. First pass: Handle Spotlight annotations if any
        spotlights = [a for a in annotations if a.type == AnnotationType.SPOTLIGHT]
        if spotlights:
            canvas = cls._apply_spotlights(canvas, spotlights)

        # 2. Second pass: Draw highlighters
        highlighters = [a for a in annotations if a.type == AnnotationType.HIGHLIGHTER]
        if highlighters:
            hl_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            draw_hl = ImageDraw.Draw(hl_layer)
            for hl in highlighters:
                x1, y1 = hl.start_pos
                x2, y2 = hl.end_pos
                rx1, rx2 = min(x1, x2), max(x1, x2)
                ry1, ry2 = min(y1, y2), max(y1, y2)
                # Fluorescent translucent yellow
                fill_color = (255, 235, 59, 110)
                draw_hl.rectangle([rx1, ry1, rx2, ry2], fill=fill_color)
            canvas = Image.alpha_composite(canvas, hl_layer)

        # 3. Third pass: Vector shapes, arrows, and step numbers
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()

        for a in annotations:
            if a.type == AnnotationType.RECTANGLE:
                x1, y1 = a.start_pos
                x2, y2 = a.end_pos
                draw.rectangle(
                    [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
                    outline=a.color,
                    width=a.stroke_width
                )

            elif a.type == AnnotationType.ARROW:
                cls._draw_pil_arrow(draw, a)

            elif a.type == AnnotationType.STEP_NUMBER:
                cls._draw_pil_step_number(draw, a, font)

        return canvas

    @classmethod
    def _apply_spotlights(cls, image: Image.Image, spotlights: List[Annotation]) -> Image.Image:
        """Darkens entire image except for the spotlighted bounding boxes."""
        dim_layer = Image.new("RGBA", image.size, (0, 0, 0, 130))
        draw_dim = ImageDraw.Draw(dim_layer)

        # Cut out clear holes for each spotlight
        for spot in spotlights:
            x1, y1 = spot.start_pos
            x2, y2 = spot.end_pos
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            draw_dim.rectangle([rx1, ry1, rx2, ry2], fill=(0, 0, 0, 0))

        res = Image.alpha_composite(image, dim_layer)
        draw_res = ImageDraw.Draw(res)

        # Draw subtle border around spotlight
        for spot in spotlights:
            x1, y1 = spot.start_pos
            x2, y2 = spot.end_pos
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            draw_res.rectangle([rx1, ry1, rx2, ry2], outline=(255, 255, 255, 180), width=1)

        return res

    @classmethod
    def _draw_pil_arrow(cls, draw: ImageDraw.ImageDraw, a: Annotation):
        x1, y1 = a.start_pos
        x2, y2 = a.end_pos

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 5:
            return

        angle = math.atan2(dy, dx)
        head_len = min(18.0, length * 0.4)
        head_angle = math.pi / 6.0  # 30 degrees

        # Draw main arrow shaft
        draw.line([(x1, y1), (x2, y2)], fill=a.color, width=a.stroke_width)

        # Arrowhead points
        p1_x = x2 - head_len * math.cos(angle - head_angle)
        p1_y = y2 - head_len * math.sin(angle - head_angle)

        p2_x = x2 - head_len * math.cos(angle + head_angle)
        p2_y = y2 - head_len * math.sin(angle + head_angle)

        draw.polygon([(x2, y2), (p1_x, p1_y), (p2_x, p2_y)], fill=a.color)

    @classmethod
    def _draw_pil_step_number(cls, draw: ImageDraw.ImageDraw, a: Annotation, font: ImageFont.ImageFont):
        cx, cy = a.start_pos
        r = a.radius

        # Circle badge
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=a.color, outline=(255, 255, 255, 220), width=1)

        # Centered step number text
        draw.text((cx, cy), a.text, fill=(255, 255, 255, 255), anchor="mm", font=font)

    # --------------------------------------------------------------------------
    # Interactive QPainter Rendering (Overlay integration)
    # --------------------------------------------------------------------------

    @classmethod
    def render_with_qpainter(
        cls,
        painter: QPainter,
        annotations: List[Annotation],
        origin_offset: Tuple[int, int] = (0, 0)
    ):
        """Renders annotations using QPainter for real-time interactive canvas."""
        ox, oy = origin_offset
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for a in annotations:
            qcol = QColor(*a.color)
            pen = QPen(qcol, a.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

            if a.type == AnnotationType.RECTANGLE:
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                x1, y1 = a.start_pos[0] + ox, a.start_pos[1] + oy
                x2, y2 = a.end_pos[0] + ox, a.end_pos[1] + oy
                rect = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                painter.drawRoundedRect(rect, 4.0, 4.0)

            elif a.type == AnnotationType.HIGHLIGHTER:
                hl_color = QColor(255, 235, 59, 100)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(hl_color))
                x1, y1 = a.start_pos[0] + ox, a.start_pos[1] + oy
                x2, y2 = a.end_pos[0] + ox, a.end_pos[1] + oy
                rect = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                painter.drawRect(rect)

            elif a.type == AnnotationType.ARROW:
                cls._draw_qt_arrow(painter, a, ox, oy)

            elif a.type == AnnotationType.STEP_NUMBER:
                cls._draw_qt_step_number(painter, a, ox, oy)

        painter.restore()

    @classmethod
    def _draw_qt_arrow(cls, painter: QPainter, a: Annotation, ox: int, oy: int):
        x1, y1 = a.start_pos[0] + ox, a.start_pos[1] + oy
        x2, y2 = a.end_pos[0] + ox, a.end_pos[1] + oy

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 5:
            return

        angle = math.atan2(dy, dx)
        head_len = min(16.0, length * 0.4)
        head_angle = math.pi / 6.0

        qcol = QColor(*a.color)
        pen = QPen(qcol, a.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Triangle head
        p1 = QPointF(x2 - head_len * math.cos(angle - head_angle), y2 - head_len * math.sin(angle - head_angle))
        p2 = QPointF(x2 - head_len * math.cos(angle + head_angle), y2 - head_len * math.sin(angle + head_angle))
        poly = QPolygonF([QPointF(x2, y2), p1, p2])

        painter.setBrush(QBrush(qcol))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(poly)

    @classmethod
    def _draw_qt_step_number(cls, painter: QPainter, a: Annotation, ox: int, oy: int):
        cx, cy = a.start_pos[0] + ox, a.start_pos[1] + oy
        r = a.radius

        qcol = QColor(*a.color)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        painter.setBrush(QBrush(qcol))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        text_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, a.text)
