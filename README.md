# RedactSnap

<div align="center">

<img src="https://img.shields.io/badge/RedactSnap-v0.5.0-3B82F6?style=for-the-badge&logo=shield&logoColor=white" alt="RedactSnap v0.5.0" />

### The Privacy-First Desktop Screenshot Autopilot

**Automatic secret masking • 100% offline OCR • Vector annotations • Studio canvas • Screen recording**

[![GitHub Release](https://img.shields.io/github/v/release/AmhetCnaa/RedactSnap?style=flat-square&color=3B82F6)](https://github.com/AmhetCnaa/RedactSnap/releases)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20(ONNX)-4B5563?style=flat-square)](https://github.com/RapidAI/RapidOCR)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/AmhetCnaa/RedactSnap)
[![Tests](https://img.shields.io/badge/Tests-42%2F42%20Passing-10B981?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square)](https://opensource.org/licenses/MIT)

<br/>

[Overview](#-overview) •
[Quickstart](#-quickstart) •
[Core Capabilities](#-core-capabilities) •
[Shortcuts & Toolbar](#-shortcuts--toolbar) •
[Security & Redaction Engine](#-security--redaction-engine) •
[Studio Themes](#-studio-themes) •
[Feature Comparison](#-feature-comparison)

</div>

---

## 💡 Overview

**RedactSnap** is a high-performance desktop screenshot tool designed for developers, security engineers, and content creators. It bridges the gap between fast system utilities (like Windows Snipping Tool) and premium design-centric software (like CleanShot X) — while adding **intelligent, zero-cloud secret redaction**.

Whenever you capture a screen area containing API keys, private credentials, passwords, or personal data (PII), RedactSnap can automatically detect and blur them locally before your screenshot leaves your machine.

---

## ⚡ Quickstart

### Option 1: Standalone Portable `.exe` (Zero Setup)

No Python installation required. Download and run:

1. Go to the [**Releases**](https://github.com/AmhetCnaa/RedactSnap/releases) page.
2. Download `RedactSnap-v0.5.0-x64.exe`.
3. Double-click to launch. It will reside quietly in your Windows system tray.
4. Press `PrintScreen` or `Ctrl+Shift+S` to capture anytime.

---

### Option 2: Run from Source (Python 3.10+)

```powershell
# 1. Clone the repository
git clone https://github.com/AmhetCnaa/RedactSnap.git
cd RedactSnap

# 2. Set up virtual environment (using uv or venv)
uv venv --python 3.12
.venv\Scripts\activate

# 3. Install dependencies
uv pip install -e ".[ocr-rapid,uploader,dev]"
```

#### Launching Modes

| Command | Description |
| :--- | :--- |
| `python -m redactsnap daemon` | **Recommended:** Runs silently in background/system tray with global hotkeys. |
| `python -m redactsnap capture` | **One-Shot:** Immediately opens the interactive selection overlay. |

---

## ✨ Core Capabilities

### 🛡️ Smart Privacy Redaction (Opt-in)
- **Zero-Cloud Guarantee:** Runs 100% locally on your machine using SIMD-accelerated ONNX neural networks.
- **Multi-Class Detection:** Detects cloud secrets (AWS, OpenAI, GitHub, Stripe, Anthropic), JWT tokens, private keys, passwords, emails, phone numbers, credit cards (Luhn-checked), and Turkish ID numbers (TCKN).
- **High-Entropy Secret Detection:** Employs Shannon Entropy calculations ($H \ge 3.8$) to catch random generated passwords without flagging normal sentences.
- **Aesthetic Masking:** Applies smooth feathered Gaussian blurs or modern dark pill badges.
- **Non-Intrusive by Default:** Selections start clean; click `[🛡️ Redact]` to instantly toggle masking on and off.

### ⚡ Instant Save & Copy Workflow
- Press `Enter` or click `[💾 Save]` / `[📋 Copy]`:
  - **Auto-saves** directly to your Windows `Pictures\Screenshots\` folder with a timestamped filename.
  - **Copies** the image directly to your clipboard.
  - **Notifies** you with an unobtrusive on-screen HUD toast notification.
  - No blocking modal dialogs slowing down your workflow.

### ✏️ Vector Annotations
- **Step Badges:** Click anywhere to drop numbered markers (`①`, `②`, `③`) that auto-increment for bug reporting and guides.
- **Vectors & Shapes:** Draw razor-sharp arrows and clean rectangular bounding boxes.
- **Highlighter:** Fluorescent neon highlighter that softly overlays text without masking underlying words.
- **Spotlight:** Dim surrounding screen area to focus visual attention on a specific UI element.

### 🎨 Studio Canvas & Social Beautifier
- Wrap any screenshot inside modern Raycast- & Linear-inspired multi-stop gradient backdrops.
- Features multi-tier soft diffuse drop shadows and optional macOS-style traffic light window controls.

### 📝 Offline OCR ("Copy as Text")
- Built-in RapidOCR (ONNX) engine extracts all text from your selection with sub-second latency.
- Click `[📝 OCR]` to copy pure text straight into your clipboard without sending pixels to any cloud API.

### 🎥 Screen Recording & Scrolling Capture
- **GIF & MP4 Recording:** Record your selected region at 30/60 FPS with live timer HUD and pre-redaction masking.
- **Scrolling Stitching:** Seamlessly captures long code files, terminal outputs, or web pages into one continuous vertical image using OpenCV template cross-correlation.

---

## ⌨️ Shortcuts & Toolbar

When you trigger a capture (`PrintScreen` or `Ctrl+Shift+S`), a floating glassmorphism toolbar appears near your selection:

```text
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │  [📋 Copy] [🛡️ Redact] [🎨 Frame] [✏️ Draw] [📝 OCR] [⏺ Record] [🔗 Share] [💾 Save]  │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

| Key / Control | Action | Details |
| :--- | :--- | :--- |
| `PrintScreen` or `Ctrl+Shift+S` | **Trigger Capture** | Opens fullscreen capture overlay with 8x pixel loupe |
| `Left Click + Drag` | **Select Region** | Defines screenshot boundaries |
| `Enter` | **Instant Save & Copy** | Saves to `Pictures\Screenshots\` and copies to clipboard |
| `Escape` or `Right Click` | **Dismiss** | Cancels overlay without copying |
| `Arrow Keys` | **1px Fine Nudge** | Adjusts selection rectangle (Hold `Shift` for 10px) |
| `[🛡️ Redact]` | **Toggle Privacy Mask** | Activates or disables secret redaction |
| `[🎨 Frame]` | **Cycle Studio Canvas** | Switches background gradients (Obsidian, Sunset, etc.) |
| `[✏️ Draw]` | **Annotation Menu** | Access Step Badges (`①`), Arrows, Boxes, Highlighter, Spotlight |
| `[📝 OCR]` | **Extract Text** | Extracts OCR text straight to clipboard |
| `[⏺ Record]` | **Record Screen** | Records selection to animated `.gif` or `.mp4` |
| `[🔗 Share]` | **Instant URL** | Uploads anonymously to Imgur/S3 and copies public URL |
| `Ctrl+Z` | **Undo** | Removes the last drawn annotation |

---

## 🛡️ Security & Redaction Engine

RedactSnap uses a layered dual-pass pipeline to catch sensitive data:

1. **Deterministic Pattern Matcher:**
   - **Cloud & API Keys:** OpenAI (`sk-...`), AWS (`AKIA...`), GitHub (`ghp_...`, `gho_...`), Anthropic (`sk-ant-...`), Stripe (`sk_live_...`).
   - **Tokens & Certificates:** JWT tokens (`eyJh...`), PEM Private Keys (`-----BEGIN ... PRIVATE KEY-----`).
   - **Credentials:** Password fields matching `password:`, `şifre;`, `parola=`, etc.
   - **PII & Finance:** Credit card numbers (verified via **Luhn algorithm**), Emails, IPv4 addresses, Turkish National IDs (TCKN contextual & mathematical check).
2. **Heuristic Shannon Entropy Engine:**
   - Calculates statistical information entropy $H(X) = -\sum P(x) \log_2 P(x)$ on alphanumeric tokens.
   - Accurately catches high-entropy randomized strings, API hashes, and secret salts ($H \ge 3.8$) while preventing false positives on natural language, usernames, and dates.

---

## 🎨 Studio Themes

Enhance presentations and social media shares with built-in presets:

| Theme | Tone | Preview Colors |
| :--- | :--- | :--- |
| **Obsidian Dark** | Linear / Stealth | Deep navy slate (`#090D16` → `#18202F` → `#0F172A`) |
| **Sunset Warmth** | macOS Monterey | Royal purple to electric magenta and warm coral |
| **Emerald Code** | Terminal Green | Deep forest to bright neon mint and cyan |
| **Cyber Purple** | Raycast Violet | Midnight violet with soft lavender accents |
| **Hyper Blue** | Keynote Electric | Classic Apple sapphire to clean sky cyan |
| **Midnight Amber**| Minimal Charcoal | Titanium dark gray with warm amber glow |
| **Transparent** | Clean Window | Window chrome with soft drop shadow on clear alpha |

---

## ⚖️ Feature Comparison

| Feature | **RedactSnap** | **CleanShot X** | **ShareX** | **Flameshot** |
| :--- | :---: | :---: | :---: | :---: |
| **License** | **Free & Open Source (MIT)** | Paid ($29+) | Free & Open Source | Free & Open Source |
| **Platform** | **Windows & Linux** | macOS Only | Windows Only | Cross-Platform |
| **Automatic Secret Redaction** | ✅ **Built-in (Zero-Cloud)** | ❌ Manual | ❌ Manual | ❌ Manual |
| **Offline Local OCR** | ✅ **RapidOCR (ONNX)** | ⚠️ macOS Native | ⚠️ Requires Tesseract | ❌ Plugin dependent |
| **Numbered Step Badges (① ②)** | ✅ **Built-in** | ✅ Built-in | ⚠️ Complex setup | ❌ No |
| **Studio Gradient Canvas** | ✅ **Built-in (7 Presets)**| ⚠️ Basic | ⚠️ Manual workflow | ❌ No |
| **Instant Save & Clipboard** | ✅ **1-Click / Enter** | ✅ Yes | ⚠️ Config required | ⚠️ Config required |
| **GIF / MP4 Recording** | ✅ **Built-in** | ✅ Built-in | ✅ Built-in | ❌ No |
| **Single Portable Executable** | ✅ **Yes (Zero Install)** | ❌ N/A | ⚠️ Installer | ⚠️ Installer |

---

## 🧪 Developer & Quality Verification

RedactSnap is backed by automated unit and integration tests covering capture pipelines, redaction accuracy, OCR preprocessing, and UI interactions:

```powershell
pytest -v
```

```text
tests/test_annotations.py .. (3 passed)
tests/test_capture.py     ...... (6 passed)
tests/test_recorder.py    ... (3 passed)
tests/test_redaction.py   .............. (14 passed)
tests/test_scroller.py    .. (2 passed)
tests/test_studio.py      ..... (5 passed)
tests/test_ui.py          ..... (5 passed)
tests/test_uploader.py    .... (4 passed)

======================= 42 passed in 5.85s =======================
```

### Packaging into Standalone Binary
To compile your own executable using PyInstaller:

```powershell
python scripts/build_exe.py
```
The compiled binary will be generated at `dist/RedactSnap-v0.5.0-x64.exe`.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

<div align="center">
Built for engineers, creators, and privacy-conscious teams worldwide.
</div>
