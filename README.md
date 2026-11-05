# 📸 RedactSnap

<div align="center">

```text
  ____           _            _   ____                    
 |  _ \ ___   __| | __ _  ___| |_/ ___| _ __   __ _ _ __  
 | |_) / _ \ / _` |/ _` |/ __| __\___ \| '_ \ / _` | '_ \ 
 |  _ <  __/| (_| | (_| | (__| |_ ___) | | | | (_| | |_) |
 |_| \_\___| \__,_|\__,_|\___|\__|____/|_| |_|\__,_| .__/ 
                                                   |_|    
```

### *The Open-Source, Privacy-First Desktop Screenshot Autopilot*
**Auto-redaction of secrets • Offline OCR • Vector annotations • Screen recording (GIF/MP4) • Scrolling stitching • Social canvas**

[![Version](https://img.shields.io/badge/Version-0.5.0-blue.svg)](https://github.com/AmhetCnaa/RedactSnap/releases)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20(ONNX)-blue)](https://github.com/RapidAI/RapidOCR)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey?logo=windows&logoColor=white)](https://github.com/AmhetCnaa/RedactSnap)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-36%2F36%20Passed-brightgreen)](tests/)

---

[Key Features](#-key-features) •
[Why RedactSnap?](#-why-redactsnap) •
[Quickstart](#-quickstart) •
[Standalone Executable](#-portable-executable) •
[Interactive Controls](#-shortcuts--controls) •
[Architecture](#-architecture)

</div>

---

## ⚡ Key Features

- **🛡️ In-Flight Auto-Redaction:** Detects API keys (OpenAI, AWS, GitHub, Stripe, Anthropic), JWT tokens, passwords, emails, credit cards (Luhn checksum), Turkish ID (TCKN), IPv4, and high-entropy secrets using Shannon Entropy $H(X)$. Smooth feathered Gaussian blur or modern dark pills.
- **✏️ Smart Vector Annotations:**
  - **Auto-Incrementing Step Numbers:** Click to drop `①`, `②`, `③` numbered circular badges for bug reports and walkthroughs.
  - **Vector Arrows & Boxes:** Pixel-sharp arrows and clean outlined boxes.
  - **Translucent Highlighter:** Fluorescent neon yellow highlighter that blends over text without obscuring readability.
  - **Spotlight Focus:** Darkens the surrounding area to draw instant visual focus to a specific element.
- **🎥 Live Screen Recording (GIF / MP4):** One-click recording of your selection at 30/60 FPS with real-time timer HUD. Exports ultra-lightweight animated `.gif` or `.mp4` with pre-redaction masking!
- **📜 Vertical Scrolling Screenshot & Stitching:** Automatically captures long web pages, terminal logs, or code documents using OpenCV template matching to create one tall continuous image.
- **📝 1-Click Offline OCR ("Copy as Text"):** Extract all text from your selection straight into your clipboard using local ONNX inference models. Zero external software setup, zero cloud calls.
- **🎨 Social Studio Canvas:** Transform raw screenshots into social-media-ready graphics with Apple & Linear-grade multi-stop gradients, 3-tier diffuse soft drop shadows, rounded corners, and macOS traffic-light window frames.
- **🔗 Zero-Server Instant Link Sharing:** 1-click anonymous upload to Imgur or personal Cloudflare R2 / AWS S3 / MinIO buckets with auto-copy link to clipboard.
- **🔍 8x Pixel Loupe:** CleanShot-grade pixel magnifier showing real-time RGB hex color codes, coordinates, and pixel grids during selection.
- **🔒 100% Zero-Cloud:** Never sends your images or credentials anywhere unless you explicitly choose to upload.

---

## 🥊 Why RedactSnap?

| Feature | **RedactSnap v0.5.0** | **CleanShot X** | **Flameshot** | **ShareX** |
| :--- | :---: | :---: | :---: | :---: |
| **Open Source & Free** | ✅ **Yes (MIT)** | ❌ Paid ($29+) | ✅ Yes | ✅ Yes |
| **Cross-Platform (Win/Linux)**| ✅ **Yes** | ❌ macOS Only | ✅ Yes | ❌ Win Only |
| **Auto-Redact Secrets / PII** | ✅ **Automatic (ONNX + Entropy)** | ❌ Manual | ❌ Manual | ❌ Manual |
| **100% Offline Local OCR** | ✅ **RapidOCR (ONNX)** | ⚠️ Native macOS | ❌ Plugin | ⚠️ Tesseract.exe |
| **Numbered Step Badges (① ② ③)**| ✅ **Built-in** | ✅ Yes | ❌ No | ⚠️ Complex |
| **Vector Arrows & Highlighter** | ✅ **Built-in** | ✅ Yes | ⚠️ Basic | ⚠️ Complex |
| **GIF / MP4 Recording** | ✅ **Built-in (with Auto-Masking)** | ✅ Yes | ❌ No | ✅ Yes |
| **Vertical Scrolling Stitching** | ✅ **OpenCV Cross-Correlation** | ✅ Yes | ❌ No | ⚠️ Manual |
| **Social Studio Canvas (Gradients)**| ✅ **7 Designer Themes** | ⚠️ Basic | ❌ No | ⚠️ Complex |
| **Standalone Portable .exe** | ✅ **Single-file (Zero Python needed)** | ❌ N/A | ⚠️ Installer | ⚠️ Installer |

---

## 🚀 Quickstart

### Option A: Portable Standalone `.exe` (No Python Required)
Download the latest `RedactSnap-v0.5.0-x64.exe` from the [Releases](https://github.com/AmhetCnaa/RedactSnap/releases) page and run it directly!

### Option B: From Source (Python 3.10+)

```powershell
# Clone the repository
git clone https://github.com/AmhetCnaa/RedactSnap.git
cd RedactSnap

# Create and activate virtual environment with uv
uv venv --python 3.12
.venv\Scripts\activate

# Install package in editable mode
uv pip install -e ".[ocr-rapid,uploader,dev]"
```

#### 🔔 Background Daemon Mode (Recommended Daily Use)
Runs silently in your Windows System Tray and registers global hotkeys (`PrintScreen` or `Ctrl+Shift+S`):

```powershell
python -m redactsnap daemon
```

#### ⚡ One-Shot Capture Mode
Launches the interactive snipping overlay directly:

```powershell
python -m redactsnap capture
```

---

## 🎮 Shortcuts & Controls

```text
 ┌────────────────────────────────────────────────────────────────────────────────┐
 │  [📋 Copy] [🛡️ Redact] [🎨 Frame] [✏️ Draw] [📝 OCR] [⏺ Record] [🔗 Share] [💾 Save] │
 └────────────────────────────────────────────────────────────────────────────────┘
```

| Action | Shortcut / Trigger | Description |
| :--- | :--- | :--- |
| **Trigger Snip** | `PrintScreen` or `Ctrl+Shift+S` | Opens full-screen virtual desktop overlay in <15ms |
| **Select Region** | `Left Click + Drag` | Defines selection rectangle with 8x magnifier loupe |
| **Copy Image** | `Enter` or `Ctrl+C` | Copies capture to clipboard and closes |
| **Save Image** | `Ctrl+S` or `[💾 Save]` | Opens file dialog (PNG / JPEG / WebP) |
| **Cancel** | `Escape` or `Right Click` | Dismisses overlay without copying |
| **Undo Draw** | `Ctrl+Z` or `[↩️ Undo]` | Removes last annotation |
| **1px Nudge** | `Arrow Keys` | Moves active selection by 1 pixel (Shift for 10px) |
| **Live Redact** | `[🛡️ Redact]` | Toggles auto-redaction on active selection |
| **Cycle Frames** | `[🎨 Frame]` | Cycles gradient themes: Obsidian → Sunset → Cyber Purple → Emerald... |
| **Annotate** | `[✏️ Draw]` | Toggles Step Numbers, Arrows, Rectangles, Highlighters, Spotlights |
| **Record GIF/MP4**| `[⏺ Record]` | Starts screen recording of selected box with timer HUD |
| **Upload Link** | `[🔗 Share]` | Uploads to Imgur / S3 and copies public URL to clipboard |
| **Copy Text** | `[📝 OCR]` | Extracts text to clipboard with floating toast notification |

---

## 🎨 Studio Canvas Presets

- 🌌 **Obsidian Dark:** Linear-style deep stealth dark space (`#090D16` → `#18202F` → `#0F172A`).
- 🌅 **Sunset Warmth:** macOS Monterey dusk with royal purple, electric magenta, and warm coral.
- 🌲 **Emerald Code:** Terminal forest green, bright mint, and cyan aqua.
- 🔮 **Cyber Purple:** Raycast ultraviolet deep violet and soft lavender.
- 🌊 **Hyper Blue:** Apple keynote clean electric navy, sapphire, and sky cyan.
- 🍯 **Midnight Amber:** Titanium charcoal and warm golden honey.
- 🪟 **Transparent Canvas:** Floating window with soft drop shadows on a transparent alpha background.

---

## 📦 Building the Standalone Executable

To compile RedactSnap into a single, zero-dependency `RedactSnap-v0.5.0-x64.exe`:

```powershell
python scripts/build_exe.py
```

The resulting binary will be placed inside `dist/`.

---

## 🧪 Automated Testing

RedactSnap is verified with **36 comprehensive unit tests**:

```powershell
pytest -v
```

```text
tests/test_annotations.py ... (3 passed)
tests/test_capture.py     ...... (6 passed)
tests/test_recorder.py    ... (3 passed)
tests/test_redaction.py   ........ (8 passed)
tests/test_scroller.py    .. (2 passed)
tests/test_studio.py      ..... (5 passed)
tests/test_ui.py          ..... (5 passed)
tests/test_uploader.py    .... (4 passed)

====================== 36 passed in 6.24s ======================
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">
Made with ❤️ for developers, creators, and privacy advocates everywhere.
</div>
