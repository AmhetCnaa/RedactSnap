"""
Shared pytest fixtures for RedactSnap tests.
"""

import sys
import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists across all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app
