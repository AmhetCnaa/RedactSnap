"""
Build script to compile RedactSnap into a standalone portable Windows executable (.exe).
Bundles PyQt6, RapidOCR ONNX models, and dependencies using PyInstaller.
"""

import os
import sys
import subprocess
import shutil

APP_VERSION = "0.5.0"
EXE_NAME = f"RedactSnap-v{APP_VERSION}-x64"


def locate_rapidocr_data() -> str:
    """Finds rapidocr_onnxruntime package location to bundle ONNX model files."""
    try:
        import rapidocr_onnxruntime
        pkg_dir = os.path.dirname(rapidocr_onnxruntime.__file__)
        sep = ";" if sys.platform.startswith("win") else ":"
        return f"{pkg_dir}{sep}rapidocr_onnxruntime"
    except Exception as e:
        print(f"Warning: Could not locate rapidocr_onnxruntime directory: {e}")
        return ""


def build():
    print(f"=== Building {EXE_NAME} Standalone Binary ===")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    entrypoint = os.path.join(project_root, "src", "redactsnap", "__main__.py")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={EXE_NAME}",
        f"--paths={os.path.join(project_root, 'src')}",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=pynput",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=pynput.mouse",
        "--hidden-import=rapidocr_onnxruntime",
        "--hidden-import=onnxruntime",
        "--hidden-import=imageio",
        "--hidden-import=cv2",
        "--hidden-import=requests",
    ]

    ocr_data = locate_rapidocr_data()
    if ocr_data:
        cmd.append(f"--add-data={ocr_data}")

    cmd.append(entrypoint)

    print("Executing PyInstaller command:")
    print(" ".join(cmd))

    ret = subprocess.run(cmd, cwd=project_root)
    if ret.returncode == 0:
        dist_exe = os.path.join(project_root, "dist", f"{EXE_NAME}.exe")
        print(f"\n[SUCCESS] Build successful! Standalone executable created at:\n   {dist_exe}")
    else:
        print(f"\n[FAILED] Build failed with exit code: {ret.returncode}")
        sys.exit(ret.returncode)


if __name__ == "__main__":
    build()
