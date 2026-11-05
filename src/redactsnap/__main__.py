"""
Entrypoint for RedactSnap desktop application.
"""

import sys
import argparse
from PyQt6.QtWidgets import QApplication

from redactsnap.app import RedactSnapApp


def main():
    parser = argparse.ArgumentParser(description="RedactSnap: Privacy-first Screenshot Autopilot")
    subparsers = parser.add_subparsers(dest="command")

    # Command: capture (one-shot instant capture)
    subparsers.add_parser("capture", help="Trigger instant one-shot snipping overlay")

    # Command: daemon (background system tray with global hotkeys)
    subparsers.add_parser("daemon", help="Run in background system tray listening for PrintScreen / Ctrl+Shift+S")

    args = parser.parse_args()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Don't quit when overlay closes if running in background daemon mode
    is_one_shot = (args.command == "capture")
    app.setQuitOnLastWindowClosed(is_one_shot)

    snap_app = RedactSnapApp(one_shot=is_one_shot)
    snap_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
