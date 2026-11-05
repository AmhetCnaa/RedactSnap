# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect RapidOCR ONNX models and yaml configs safely
datas = []
try:
    datas += collect_data_files('rapidocr_onnxruntime')
except Exception as e:
    print(f"Notice: collect_data_files for rapidocr_onnxruntime skipped: {e}")

try:
    datas += collect_data_files('imageio_ffmpeg')
except Exception as e:
    print(f"Notice: collect_data_files for imageio_ffmpeg skipped: {e}")

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'imageio',
    'cv2',
    'requests',
    'redactsnap',
]

try:
    hiddenimports += collect_submodules('pynput')
except Exception:
    pass

try:
    hiddenimports += collect_submodules('rapidocr_onnxruntime')
except Exception:
    pass

try:
    hiddenimports += collect_submodules('imageio_ffmpeg')
except Exception:
    pass

a = Analysis(
    ['src/redactsnap/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RedactSnap-v0.5.0-x64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
