"""Generates high-aesthetic visual showcase banners and cards for RedactSnap's README.md."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Fonts
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"

def get_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_diffuse_shadow(draw: ImageDraw.ImageDraw, base_img: Image.Image, box, radius=16, blur=30, opacity=120):
    """Draws a multi-tier Apple/Linear style soft diffuse drop shadow."""
    shadow = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    
    # Tier 1 - Wide ambient glow
    s_draw.rounded_rectangle(
        [box[0] - 6, box[1] + 16, box[2] + 6, box[3] + 28],
        radius=radius,
        fill=(0, 0, 0, int(opacity * 0.4))
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    
    # Tier 2 - Medium shadow
    s_draw2 = ImageDraw.Draw(shadow)
    s_draw2.rounded_rectangle(
        [box[0] - 2, box[1] + 8, box[2] + 2, box[3] + 16],
        radius=radius,
        fill=(0, 0, 0, int(opacity * 0.6))
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur // 2))
    
    base_img.alpha_composite(shadow)


def generate_hero_banner():
    width, height = 1200, 680
    img = Image.new("RGBA", (width, height), (10, 14, 22, 255))
    
    # 1. Background radial gradient / ambient glows
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([width // 2 - 400, -100, width // 2 + 400, 500], fill=(37, 99, 235, 35))
    g_draw.ellipse([width - 350, height // 2 - 200, width + 250, height // 2 + 300], fill=(139, 92, 246, 30))
    g_draw.ellipse([-150, height - 300, 450, height + 200], fill=(16, 185, 129, 25))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img.alpha_composite(glow)
    
    draw = ImageDraw.Draw(img)
    
    # 2. Window Box Dimensions
    win_x1, win_y1 = 150, 70
    win_x2, win_y2 = 1050, 520
    
    # Draw diffuse shadow
    draw_diffuse_shadow(draw, img, (win_x1, win_y1, win_x2, win_y2), radius=16, blur=36, opacity=140)
    
    # Re-acquire draw after composite
    draw = ImageDraw.Draw(img)
    
    # 3. Main Window Body
    draw.rounded_rectangle([win_x1, win_y1, win_x2, win_y2], radius=16, fill=(15, 23, 42, 250), outline=(51, 65, 85, 255), width=1)
    
    # Titlebar
    title_h = 42
    draw.rounded_rectangle([win_x1, win_y1, win_x2, win_y1 + title_h], radius=16, fill=(30, 41, 59, 255))
    # Flatten bottom corners of titlebar
    draw.rectangle([win_x1, win_y1 + 20, win_x2, win_y1 + title_h], fill=(30, 41, 59, 255))
    draw.line([win_x1, win_y1 + title_h, win_x2, win_y1 + title_h], fill=(51, 65, 85, 255), width=1)
    
    # Traffic light dots
    draw.ellipse([win_x1 + 18, win_y1 + 14, win_x1 + 32, win_y1 + 28], fill=(255, 95, 86))
    draw.ellipse([win_x1 + 40, win_y1 + 14, win_x1 + 54, win_y1 + 28], fill=(255, 189, 46))
    draw.ellipse([win_x1 + 62, win_y1 + 14, win_x1 + 76, win_y1 + 28], fill=(39, 201, 63))
    
    # Window Title
    font_title = get_font(FONT_REGULAR, 14)
    draw.text((win_x1 + (win_x2 - win_x1) // 2 - 120, win_y1 + 11), "production_secrets.env — RedactSnap Studio", fill=(148, 163, 184), font=font_title)
    
    # Code Content
    font_mono = get_font(FONT_MONO, 16)
    font_bold = get_font(FONT_BOLD, 15)
    font_tag = get_font(FONT_BOLD, 11)
    
    lines = [
        ("# 🔐 Production API Credentials & Cloud Secrets", (100, 116, 139)),
        ("OPENAI_API_KEY = \"sk-proj-91aKc98fGq01vX2...\"", (226, 232, 240)),
        ("AWS_SECRET_ACCESS_KEY = \"AKIAIOSFODNN7EXAMPLE...\"", (226, 232, 240)),
        ("STRIPE_SECRET_KEY = \"sk_live_51Mabcdef982134...\"", (226, 232, 240)),
        ("DATABASE_PASSWORD = \"Sup3rS3cr3t#P@ssw0rd!2026\"", (226, 232, 240)),
        ("USER_NATIONAL_ID = \"34810293842\"  # Turkish Citizen ID", (226, 232, 240)),
        ("JWT_AUTH_BEARER = \"eyJhGciOiJIUzI1NiIsInR5cCI6...\"", (226, 232, 240)),
    ]
    
    curr_y = win_y1 + 64
    for idx, (code_text, color) in enumerate(lines):
        # Line numbers
        draw.text((win_x1 + 24, curr_y), f"{idx+1:2d}", fill=(71, 85, 105), font=font_mono)
        draw.text((win_x1 + 64, curr_y), code_text, fill=color, font=font_mono)
        curr_y += 34
    
    # 4. In-Flight Redaction Badges
    # Redact OpenAI key
    r1_box = [win_x1 + 245, win_y1 + 94, win_x1 + 540, win_y1 + 124]
    draw.rounded_rectangle(r1_box, radius=6, fill=(15, 23, 42, 255), outline=(56, 189, 248), width=1)
    draw.text((r1_box[0] + 12, r1_box[1] + 6), "[🛡️ REDACTED: OPENAI KEY]", fill=(56, 189, 248), font=font_tag)
    
    # Redact AWS Key
    r2_box = [win_x1 + 310, win_y1 + 128, win_x1 + 620, win_y1 + 158]
    draw.rounded_rectangle(r2_box, radius=6, fill=(15, 23, 42, 255), outline=(249, 115, 22), width=1)
    draw.text((r2_box[0] + 12, r2_box[1] + 6), "[🛡️ REDACTED: AWS CREDENTIAL]", fill=(249, 115, 22), font=font_tag)

    # Redact Stripe Key
    r3_box = [win_x1 + 270, win_y1 + 162, win_x1 + 560, win_y1 + 192]
    draw.rounded_rectangle(r3_box, radius=6, fill=(15, 23, 42, 255), outline=(168, 85, 247), width=1)
    draw.text((r3_box[0] + 12, r3_box[1] + 6), "[🛡️ REDACTED: STRIPE KEY]", fill=(168, 85, 247), font=font_tag)

    # Feathered Blur on Database Password
    blur_box = [win_x1 + 275, win_y1 + 196, win_x1 + 600, win_y1 + 226]
    draw.rounded_rectangle(blur_box, radius=6, fill=(30, 41, 59, 230), outline=(148, 163, 184), width=1)
    draw.text((blur_box[0] + 12, blur_box[1] + 6), "•••••••••••••••••••••••••", fill=(203, 213, 225), font=font_bold)
    
    # Redact National ID (TCKN)
    r4_box = [win_x1 + 265, win_y1 + 230, win_x1 + 450, win_y1 + 260]
    draw.rounded_rectangle(r4_box, radius=6, fill=(15, 23, 42, 255), outline=(239, 68, 68), width=1)
    draw.text((r4_box[0] + 12, r4_box[1] + 6), "[🛡️ REDACTED: TCKN]", fill=(239, 68, 68), font=font_tag)

    # 5. Smart Vector Annotations Overlay
    # Step 1: Circular Step Badge
    step1_c = (win_x1 + 570, win_y1 + 109)
    draw.ellipse([step1_c[0] - 14, step1_c[1] - 14, step1_c[0] + 14, step1_c[1] + 14], fill=(59, 130, 246))
    draw.ellipse([step1_c[0] - 14, step1_c[1] - 14, step1_c[0] + 14, step1_c[1] + 14], outline=(255, 255, 255), width=2)
    draw.text((step1_c[0] - 5, step1_c[1] - 9), "1", fill=(255, 255, 255), font=font_bold)
    
    # Step 2: Circular Step Badge
    step2_c = (win_x1 + 650, win_y1 + 143)
    draw.ellipse([step2_c[0] - 14, step2_c[1] - 14, step2_c[0] + 14, step2_c[1] + 14], fill=(168, 85, 247))
    draw.ellipse([step2_c[0] - 14, step2_c[1] - 14, step2_c[0] + 14, step2_c[1] + 14], outline=(255, 255, 255), width=2)
    draw.text((step2_c[0] - 5, step2_c[1] - 9), "2", fill=(255, 255, 255), font=font_bold)

    # Sleek Arrow pointing to redaction
    arrow_start = (win_x1 + 720, win_y1 + 90)
    arrow_end = (win_x1 + 590, win_y1 + 108)
    draw.line([arrow_start, arrow_end], fill=(56, 189, 248), width=3)
    draw.polygon([
        (arrow_end[0], arrow_end[1]),
        (arrow_end[0] + 12, arrow_end[1] - 8),
        (arrow_end[0] + 10, arrow_end[1] + 7)
    ], fill=(56, 189, 248))
    draw.text((arrow_start[0] + 10, arrow_start[1] - 8), "Local Neural OCR Masking", fill=(56, 189, 248), font=font_bold)

    # Neon Highlighter overlay
    hl_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(hl_layer)
    hl_draw.rounded_rectangle([win_x1 + 64, win_y1 + 196, win_x1 + 255, win_y1 + 224], radius=4, fill=(250, 204, 21, 90))
    img.alpha_composite(hl_layer)
    draw = ImageDraw.Draw(img)

    # 6. Floating Glassmorphism Toolbar at bottom
    tb_w, tb_h = 760, 56
    tb_x1 = width // 2 - tb_w // 2
    tb_y1 = win_y2 + 25
    tb_x2 = tb_x1 + tb_w
    tb_y2 = tb_y1 + tb_h
    
    # Shadow for toolbar
    draw_diffuse_shadow(draw, img, (tb_x1, tb_y1, tb_x2, tb_y2), radius=28, blur=24, opacity=160)
    draw = ImageDraw.Draw(img)
    
    # Glass toolbar body
    draw.rounded_rectangle([tb_x1, tb_y1, tb_x2, tb_y2], radius=28, fill=(15, 23, 42, 230), outline=(255, 255, 255, 50), width=1)
    
    # Toolbar Items
    tb_items = [
        ("📋 Copy", (226, 232, 240)),
        ("🛡️ Redact (ON)", (56, 189, 248), True),
        ("🎨 Sunset", (244, 114, 182)),
        ("✏️ Annotate", (226, 232, 240)),
        ("📝 OCR Text", (226, 232, 240)),
        ("⏺ Record", (239, 68, 68)),
        ("💾 Quick Save", (52, 211, 153))
    ]
    
    font_tb = get_font(FONT_BOLD, 13)
    curr_btn_x = tb_x1 + 20
    for item in tb_items:
        text = item[0]
        color = item[1]
        is_active = len(item) > 2 and item[2]
        
        if is_active:
            draw.rounded_rectangle([curr_btn_x - 8, tb_y1 + 10, curr_btn_x + 115, tb_y2 - 10], radius=18, fill=(30, 58, 138, 200), outline=(56, 189, 248), width=1)
            draw.text((curr_btn_x, tb_y1 + 18), text, fill=color, font=font_tb)
            curr_btn_x += 130
        else:
            draw.text((curr_btn_x, tb_y1 + 18), text, fill=color, font=font_tb)
            curr_btn_x += 98

    # Save hero banner
    img.save(ASSETS_DIR / "hero-banner.png", "PNG", optimize=True)
    print("[+] Created assets/hero-banner.png")


def generate_feature_redaction():
    """Generates a Before & After visual comparison card."""
    width, height = 1100, 380
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    
    draw = ImageDraw.Draw(img)
    font_bold = get_font(FONT_BOLD, 18)
    font_mono = get_font(FONT_MONO, 14)
    font_reg = get_font(FONT_REGULAR, 14)
    font_tag = get_font(FONT_BOLD, 12)
    
    # Left Card: BEFORE
    b_x1, b_y1, b_x2, b_y2 = 40, 40, 520, 340
    draw.rounded_rectangle([b_x1, b_y1, b_x2, b_y2], radius=16, fill=(30, 41, 59, 200), outline=(239, 68, 68, 120), width=1)
    # Header tag
    draw.rounded_rectangle([b_x1 + 20, b_y1 + 20, b_x1 + 180, b_y1 + 52], radius=8, fill=(127, 29, 29, 180))
    draw.text((b_x1 + 32, b_y1 + 26), "❌ EXPOSED SECRETS", fill=(252, 165, 165), font=font_tag)
    
    draw.text((b_x1 + 24, b_y1 + 80), "# Standard Raw Screenshot", fill=(148, 163, 184), font=font_mono)
    draw.text((b_x1 + 24, b_y1 + 115), "OPENAI_API_KEY = \"sk-proj-49fk...\"", fill=(239, 68, 68), font=font_mono)
    draw.text((b_x1 + 24, b_y1 + 150), "AWS_KEY = \"AKIAIOSFODNN7EXAMPLE\"", fill=(239, 68, 68), font=font_mono)
    draw.text((b_x1 + 24, b_y1 + 185), "DB_PASS = \"UltraSecretPassword!\"", fill=(239, 68, 68), font=font_mono)
    draw.text((b_x1 + 24, b_y1 + 220), "TCKN = \"49012345678\"", fill=(239, 68, 68), font=font_mono)
    
    draw.line([b_x1 + 20, b_y2 - 60, b_x2 - 20, b_y2 - 60], fill=(51, 65, 85), width=1)
    draw.text((b_x1 + 24, b_y2 - 45), "⚠️ Risk: Accidental credential leakage in chat or ticket", fill=(248, 113, 113), font=font_reg)

    # Right Card: AFTER
    a_x1, a_y1, a_x2, a_y2 = 580, 40, 1060, 340
    draw.rounded_rectangle([a_x1, a_y1, a_x2, a_y2], radius=16, fill=(30, 41, 59, 200), outline=(52, 211, 153, 120), width=1)
    # Header tag
    draw.rounded_rectangle([a_x1 + 20, a_y1 + 20, a_x1 + 215, a_y1 + 52], radius=8, fill=(6, 78, 59, 180))
    draw.text((a_x1 + 32, a_y1 + 26), "🛡️ REDACTSNAP AUTOPILOT", fill=(110, 231, 183), font=font_tag)
    
    draw.text((a_x1 + 24, a_y1 + 80), "# 100% Offline AI Privacy Masking", fill=(148, 163, 184), font=font_mono)
    
    # Redacted OpenAI
    draw.text((a_x1 + 24, a_y1 + 115), "OPENAI_API_KEY = ", fill=(226, 232, 240), font=font_mono)
    draw.rounded_rectangle([a_x1 + 160, a_y1 + 112, a_x1 + 370, a_y1 + 138], radius=6, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
    draw.text((a_x1 + 170, a_y1 + 116), "[🛡️ REDACTED SECRET]", fill=(56, 189, 248), font=font_tag)

    # Redacted AWS
    draw.text((a_x1 + 24, a_y1 + 150), "AWS_KEY = ", fill=(226, 232, 240), font=font_mono)
    draw.rounded_rectangle([a_x1 + 110, a_y1 + 147, a_x1 + 320, a_y1 + 173], radius=6, fill=(15, 23, 42), outline=(249, 115, 22), width=1)
    draw.text((a_x1 + 120, a_y1 + 151), "[🛡️ REDACTED KEY]", fill=(249, 115, 22), font=font_tag)

    # Feathered Blur Pass
    draw.text((a_x1 + 24, a_y1 + 185), "DB_PASS = ", fill=(226, 232, 240), font=font_mono)
    draw.rounded_rectangle([a_x1 + 110, a_y1 + 182, a_x1 + 330, a_y1 + 208], radius=6, fill=(15, 23, 42), outline=(148, 163, 184), width=1)
    draw.text((a_x1 + 120, a_y1 + 186), "•••••••••••••••••••", fill=(203, 213, 225), font=font_mono)

    # Redacted TCKN
    draw.text((a_x1 + 24, a_y1 + 220), "TCKN = ", fill=(226, 232, 240), font=font_mono)
    draw.rounded_rectangle([a_x1 + 80, a_y1 + 217, a_x1 + 260, a_y1 + 243], radius=6, fill=(15, 23, 42), outline=(239, 68, 68), width=1)
    draw.text((a_x1 + 90, a_y1 + 221), "[🛡️ REDACTED TCKN]", fill=(239, 68, 68), font=font_tag)

    draw.line([a_x1 + 20, a_y2 - 60, a_x2 - 20, a_y2 - 60], fill=(51, 65, 85), width=1)
    draw.text((a_x1 + 24, a_y2 - 45), "✓ Safe: Automatically detected and sanitized locally", fill=(52, 211, 153), font=font_reg)

    img.save(ASSETS_DIR / "feature-redaction.png", "PNG", optimize=True)
    print("[+] Created assets/feature-redaction.png")


def generate_feature_studio():
    """Generates preview swatches of the 6 Studio Canvas Themes."""
    width, height = 1100, 340
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    font_bold = get_font(FONT_BOLD, 15)
    font_reg = get_font(FONT_REGULAR, 12)
    
    themes = [
        ("Obsidian Dark", [(9, 13, 22), (24, 32, 47), (15, 23, 42)], "Stealth & Linear style"),
        ("Sunset Warmth", [(79, 70, 229), (219, 39, 119), (249, 115, 22)], "macOS Monterey Dusk"),
        ("Cyber Purple", [(88, 28, 135), (147, 51, 234), (192, 132, 252)], "Raycast Ultraviolet"),
        ("Emerald Code", [(6, 78, 59), (16, 185, 129), (56, 189, 248)], "Terminal & Matrix Green"),
        ("Hyper Blue", [(30, 58, 138), (37, 99, 235), (14, 165, 233)], "Apple Keynote Sapphire"),
        ("Midnight Amber", [(39, 39, 42), (82, 82, 91), (217, 119, 6)], "Titanium Charcoal & Gold"),
    ]
    
    card_w = 320
    card_h = 130
    gap_x = 35
    gap_y = 25
    start_x = 45
    start_y = 35
    
    for i, (name, colors, desc) in enumerate(themes):
        col = i % 3
        row = i // 3
        cx = start_x + col * (card_w + gap_x)
        cy = start_y + row * (card_h + gap_y)
        
        # Mini Canvas Background
        card_img = Image.new("RGBA", (card_w, card_h), colors[0])
        c_draw = ImageDraw.Draw(card_img)
        # 3-stop simulated gradient
        for y in range(card_h):
            ratio = y / card_h
            if ratio < 0.5:
                sub = ratio * 2
                r = int(colors[0][0] * (1 - sub) + colors[1][0] * sub)
                g = int(colors[0][1] * (1 - sub) + colors[1][1] * sub)
                b = int(colors[0][2] * (1 - sub) + colors[1][2] * sub)
            else:
                sub = (ratio - 0.5) * 2
                r = int(colors[1][0] * (1 - sub) + colors[2][0] * sub)
                g = int(colors[1][1] * (1 - sub) + colors[2][1] * sub)
                b = int(colors[1][2] * (1 - sub) + colors[2][2] * sub)
            c_draw.line([0, y, card_w, y], fill=(r, g, b, 255))
        
        # Mini Mockup Window inside
        c_draw.rounded_rectangle([30, 20, card_w - 30, card_h - 20], radius=8, fill=(15, 23, 42, 230), outline=(255, 255, 255, 60), width=1)
        # Traffic lights
        c_draw.ellipse([42, 28, 48, 34], fill=(255, 95, 86))
        c_draw.ellipse([52, 28, 58, 34], fill=(255, 189, 46))
        c_draw.ellipse([62, 28, 68, 34], fill=(39, 201, 63))
        
        # Text
        c_draw.text((45, 52), name, fill=(255, 255, 255), font=font_bold)
        c_draw.text((45, 75), desc, fill=(203, 213, 225), font=font_reg)
        
        # Border around card
        c_draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=12, outline=(255, 255, 255, 40), width=1)
        
        img.paste(card_img, (cx, cy))
        
    img.save(ASSETS_DIR / "feature-studio.png", "PNG", optimize=True)
    print("[+] Created assets/feature-studio.png")


if __name__ == "__main__":
    generate_hero_banner()
    generate_feature_redaction()
    generate_feature_studio()
    print("[DONE] All visual showcase assets successfully generated in assets/")
