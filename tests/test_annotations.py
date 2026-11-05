"""
Unit tests for Smart Annotation and Drawing Engine.
"""

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QPixmap

from redactsnap.studio.annotations import (
    Annotation,
    AnnotationType,
    AnnotationRenderer,
)


@pytest.fixture(scope="session")
def qapp():
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_annotation_creation():
    step = Annotation(
        type=AnnotationType.STEP_NUMBER,
        start_pos=(50, 50),
        end_pos=(50, 50),
        text="1"
    )
    assert step.type == AnnotationType.STEP_NUMBER
    assert step.text == "1"

    arrow = Annotation(
        type=AnnotationType.ARROW,
        start_pos=(10, 10),
        end_pos=(100, 80),
        stroke_width=4
    )
    assert arrow.type == AnnotationType.ARROW
    assert arrow.stroke_width == 4


def test_render_on_image():
    base_img = Image.new("RGBA", (300, 300), (255, 255, 255, 255))

    annotations = [
        Annotation(type=AnnotationType.STEP_NUMBER, start_pos=(50, 50), end_pos=(50, 50), text="1"),
        Annotation(type=AnnotationType.ARROW, start_pos=(50, 60), end_pos=(150, 150)),
        Annotation(type=AnnotationType.RECTANGLE, start_pos=(150, 150), end_pos=(250, 250)),
        Annotation(type=AnnotationType.HIGHLIGHTER, start_pos=(20, 20), end_pos=(120, 50)),
        Annotation(type=AnnotationType.SPOTLIGHT, start_pos=(40, 40), end_pos=(100, 100)),
    ]

    rendered = AnnotationRenderer.render_on_image(base_img, annotations)
    assert rendered.size == (300, 300)
    assert rendered.mode == "RGBA"


def test_render_with_qpainter(qapp):
    pix = QPixmap(300, 300)
    pix.fill()

    painter = QPainter(pix)
    annotations = [
        Annotation(type=AnnotationType.STEP_NUMBER, start_pos=(40, 40), end_pos=(40, 40), text="1"),
        Annotation(type=AnnotationType.ARROW, start_pos=(40, 50), end_pos=(120, 120)),
        Annotation(type=AnnotationType.RECTANGLE, start_pos=(120, 120), end_pos=(200, 200)),
        Annotation(type=AnnotationType.HIGHLIGHTER, start_pos=(10, 10), end_pos=(80, 30)),
        Annotation(type=AnnotationType.SPOTLIGHT, start_pos=(5, 5), end_pos=(50, 50)),
    ]

    AnnotationRenderer.render_with_qpainter(painter, annotations)
    painter.end()

    assert not pix.isNull()
