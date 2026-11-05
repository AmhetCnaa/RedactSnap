<div align="center">

# 📸 RedactSnap

### *The Privacy-First Desktop Screenshot Autopilot*
**Automated Secret Redaction • 100% Offline OCR • Smart Vector Annotations • Studio Canvas**

<br/>

[![Release](https://img.shields.io/github/v/release/AmhetCnaa/RedactSnap?style=for-the-badge&color=3B82F6&logo=github)](https://github.com/AmhetCnaa/RedactSnap/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/AmhetCnaa/RedactSnap)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-44%2F44%20Passing-10B981?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

<br/>
<br/>

<a href="https://github.com/AmhetCnaa/RedactSnap/releases">
  <img src="assets/hero-banner.png" alt="RedactSnap Hero Showcase" width="100%" />
</a>

<br/>
<br/>

**[⚡ Download Standalone .exe (v0.5.0)](https://github.com/AmhetCnaa/RedactSnap/releases)** •
**[✨ Key Features](#-key-features)** •
**[🛡️ Privacy Engine](#-in-flight-zero-cloud-redaction)** •
**[🎨 Studio Canvas](#-studio-social-canvas)** •
**[⌨️ Shortcuts](#-shortcuts--toolbar)** •
**[🥊 Comparison](#-feature-comparison)**

</div>

---

## ⚡ Overview

**RedactSnap** is a high-performance desktop screenshot tool designed for developers, cybersecurity teams, and content creators. It combines the instant speed of **Windows Snipping Tool** with the sleek design polish of **CleanShot X** — supercharged with **automated, 100% offline secret redaction**.

Never accidentally leak an API token, private key, or password in your Slack messages, GitHub issues, or documentation screenshots again.

---

## 🛡️ In-Flight Zero-Cloud Redaction

RedactSnap continuously parses your screen captures using local SIMD-accelerated neural networks (RapidOCR ONNX). Sensitive data is detected and masked in milliseconds with zero cloud dependencies.

<p align="center">
  <img src="assets/feature-redaction.png" alt="Before and After Redaction" width="100%" />
</p>

### What RedactSnap Detects:
- **Cloud & AI API Keys:** OpenAI (`sk-...`), AWS (`AKIA...`), GitHub (`ghp_...`, `gho_...`), Anthropic (`sk-ant-...`), Stripe (`sk_live_...`).
- **Certificates & Tokens:** JWT Bearer tokens, PEM Private Keys (`-----BEGIN RSA PRIVATE KEY-----`).
- **Passwords & Credentials:** Inline passwords in any language (`password:...`, `şifre;...`, `parola=...`).
- **Personal Data (PII):** Turkish Citizen IDs (contextual & mathematical check), Credit Cards (verified via **Luhn Algorithm**), Emails, and IPv4 addresses.
- **Shannon Entropy Engine:** Mathematical entropy filtering ($H \ge 3.8$) identifies randomly generated secret hashes while preserving normal text and dates.

> [!TIP]
> **Opt-in by Design:** Area selections start completely clean and unaltered. Click **`[🛡️ Redact]`** on the floating toolbar anytime to instantly toggle privacy masking!

---

## 🎨 Studio Social Canvas

Transform boring raw captures into gorgeous social-media-ready graphics in one click. Features multi-stop Linear- and Raycast-inspired gradients, 3-tier Apple-style diffuse drop shadows, and optional macOS window controls.

<p align="center">
  <img src="assets/feature-studio.png" alt="Studio Canvas Themes" width="100%" />
</p>

Cycle between **7 designer gradient presets** directly from the floating toolbar (`[🎨 Frame]`):
1. **🌌 Obsidian Dark:** Linear-style stealth slate (`#090D16` → `#18202F` → `#0F172A`)
2. **🌅 Sunset Warmth:** macOS Monterey dusk with royal purple, electric magenta, and warm coral
3. **🔮 Cyber Purple:** Raycast ultraviolet deep violet and soft lavender
4. **🌲 Emerald Code:** Terminal forest green, bright mint, and cyan aqua
5. **🌊 Hyper Blue:** Apple keynote sapphire navy and sky cyan
6. **🍯 Midnight Amber:** Titanium charcoal with warm golden amber
7. **🪟 Transparent:** Clean floating window with soft drop shadow on clear alpha

---

## 🚀 Key Features

<table>
  <tr>
    <td width="50%">
      <h3>⚡ Instant Save & Copy Workflow</h3>
      Press <code>Enter</code> or click <code>[💾 Save]</code> / <code>[📋 Copy]</code>:
      <ul>
        <li>Auto-saves directly to <code>Pictures\Screenshots\</code> with timestamp.</li>
        <li>Copies image directly to your clipboard.</li>
        <li>Shows unobtrusive on-screen HUD toast.</li>
        <li><b>Zero blocking dialogs</b> slowing you down.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>✏️ Smart Vector Annotations</h3>
      Add rich markup directly inside the snipping overlay:
      <ul>
        <li><b>Step Numbers:</b> Drop <code>①</code>, <code>②</code>, <code>③</code> auto-incrementing badges.</li>
        <li><b>Vector Arrows:</b> Pixel-sharp directional arrows.</li>
        <li><b>Highlighter:</b> Fluorescent neon yellow overlay.</li>
        <li><b>Spotlight:</b> Focus light on target element, dimming the rest.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>📝 1-Click Offline OCR</h3>
      Extract all text from your selection straight into your clipboard using local ONNX inference models. Zero external software setup, zero cloud calls.
    </td>
    <td width="50%">
      <h3>🎥 Screen Recording & Scroller</h3>
      Record selections at 30/60 FPS with live timer HUD and pre-redaction masking (exports <code>.gif</code> or <code>.mp4</code>). Vertical scrolling capture stitches long web pages seamlessly with OpenCV.
    </td>
  </tr>
</table>

---

## ⌨️ Shortcuts & Toolbar

```text
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │  [📋 Copy] [🛡️ Redact] [🎨 Frame] [✏️ Draw] [📝 OCR] [⏺ Record] [🔗 Share] [💾 Save]  │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

| Shortcut / Trigger | Action | Behavior |
| :--- | :--- | :--- |
| `PrintScreen` or `Ctrl+Shift+S` | **Trigger Snip** | Opens full-screen overlay with 8x pixel loupe (<15ms) |
| `Left Click + Drag` | **Select Region** | Defines screenshot area |
| `Enter` | **Instant Save & Copy** | Saves to `Pictures\Screenshots\` & copies to clipboard |
| `Escape` or `Right Click` | **Dismiss** | Cancels overlay without copying |
| `Arrow Keys` | **Fine Nudge** | Moves active selection by 1px (Hold `Shift` for 10px) |
| `[🛡️ Redact]` | **Toggle Privacy** | Toggles secret masking on active selection |
| `[🎨 Frame]` | **Cycle Studio** | Cycles Obsidian → Sunset → Cyber Purple → Emerald... |
| `[✏️ Draw]` | **Annotation Menu** | Access Step Badges (`①`), Arrows, Boxes, Highlighter, Spotlight |
| `[📝 OCR]` | **Copy Text** | Extracts OCR text straight to clipboard with toast notification |
| `[⏺ Record]` | **Record Screen** | Starts GIF/MP4 recording of selected box with timer HUD |
| `[🔗 Share]` | **Instant URL** | Uploads anonymously to Imgur/S3 and copies public URL |
| `Ctrl+Z` | **Undo** | Removes last drawn annotation |

---

## 📥 Installation & Quickstart

### Option A: Portable `.exe` (Recommended for End-Users)
No Python installation or setup required:
1. Download **`RedactSnap-v0.5.0-x64.exe`** from [**Releases**](https://github.com/AmhetCnaa/RedactSnap/releases).
2. Double click to run. RedactSnap will stay in your system tray.
3. Hit `PrintScreen` anytime to capture!

### Option B: From Source (For Developers)

```powershell
# Clone the repository
git clone https://github.com/AmhetCnaa/RedactSnap.git
cd RedactSnap

# Create virtual environment (uv or standard venv)
uv venv --python 3.12
.venv\Scripts\activate

# Install dependencies
uv pip install -e ".[ocr-rapid,uploader,dev]"

# Run in background system tray mode
python -m redactsnap daemon

# Or trigger one-shot capture
python -m redactsnap capture
```

---

## 🥊 Feature Comparison

| Feature | **RedactSnap v0.5.0** | **CleanShot X** | **ShareX** | **Flameshot** |
| :--- | :---: | :---: | :---: | :---: |
| **Price / License** | **Free & Open Source (MIT)** | Paid ($29+) | Free & Open Source | Free & Open Source |
| **Supported OS** | **Windows & Linux** | macOS Only | Windows Only | Cross-Platform |
| **In-Flight Secret Redaction**| ✅ **Automatic (Zero-Cloud)** | ❌ Manual | ❌ Manual | ❌ Manual |
| **Offline Local OCR** | ✅ **Built-in (ONNX)** | ⚠️ macOS Native | ⚠️ Requires Tesseract | ❌ Plugin |
| **Numbered Step Badges (① ②)**| ✅ **Built-in** | ✅ Built-in | ⚠️ Complex | ❌ No |
| **Studio Social Canvas** | ✅ **Built-in (7 Presets)**| ⚠️ Basic | ⚠️ Manual script | ❌ No |
| **Instant Save & Clipboard** | ✅ **1-Click / Enter** | ✅ Yes | ⚠️ Config required | ⚠️ Config required |
| **GIF / MP4 Recording** | ✅ **Built-in** | ✅ Built-in | ✅ Built-in | ❌ No |
| **Single Portable Executable** | ✅ **Yes (Zero Install)** | ❌ N/A | ⚠️ Installer | ⚠️ Installer |

---

## 🧪 Automated Testing

RedactSnap is verified by **44 comprehensive unit tests** covering capture logic, redaction patterns, asynchronous background workers, and UI responsiveness:

```powershell
pytest -v
```

```text
tests/test_annotations.py ... (3 passed)
tests/test_capture.py     ...... (6 passed)
tests/test_recorder.py    ... (3 passed)
tests/test_redaction.py   ................ (16 passed)
tests/test_scroller.py    .. (2 passed)
tests/test_studio.py      ..... (5 passed)
tests/test_ui.py          ..... (5 passed)
tests/test_uploader.py    .... (4 passed)

======================= 44 passed in 5.89s =======================
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

<div align="center">
Crafted with ❤️ for developers, creators, and privacy advocates everywhere.
</div>
