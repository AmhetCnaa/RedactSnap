"""
Unit tests for the Screen Recorder module.
"""

import os
import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect

from redactsnap.capture.recorder import ScreenRecorder


@pytest.fixture(scope="session")
def qapp():
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_recorder_initialization(qapp):
    recorder = ScreenRecorder()
    assert not recorder.is_recording
    assert recorder.fps == 30
    assert recorder.output_format == "gif"


def test_recorder_start_stop(qapp, tmp_path):
    recorder = ScreenRecorder()
    rect = QRect(100, 100, 200, 150)

    recorder.start(target_rect=rect, fps=20, output_format="gif")
    assert recorder.is_recording

    # Artificially inject 3 sample frames to test export
    sample_frame = Image.new("RGB", (200, 150), (12, 34, 56))
    recorder.frames = [sample_frame, sample_frame, sample_frame]

    out_gif = str(tmp_path / "test_recording.gif")
    result_path = recorder.stop(custom_output_path=out_gif)

    assert not recorder.is_recording
    assert result_path == out_gif
    assert os.path.exists(out_gif)
    assert os.path.getsize(out_gif) > 0


def test_recorder_mp4_export(qapp, tmp_path):
    recorder = ScreenRecorder()
    rect = QRect(0, 0, 160, 120)
    recorder.start(target_rect=rect, fps=15, output_format="mp4")

    sample_frame = Image.new("RGB", (160, 120), (200, 100, 50))
    recorder.frames = [sample_frame, sample_frame]

    out_mp4 = str(tmp_path / "test_recording.mp4")
    result_path = recorder.stop(custom_output_path=out_mp4)

    assert os.path.exists(out_mp4)
    assert os.path.getsize(out_mp4) > 0
