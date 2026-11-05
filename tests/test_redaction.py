"""
Unit tests for the redaction module: Patterns, Entropy Analyzer, Masker, and Pipeline.
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw

from redactsnap.redaction.patterns import PATTERNS, luhn_checksum_valid, tckn_valid
from redactsnap.redaction.entropy import EntropyAnalyzer
from redactsnap.redaction.masker import RedactionMasker, RedactionStyle
from redactsnap.redaction.engine import RedactionPipeline
from redactsnap.redaction.ocr.rapid import RapidOCREngine


def test_patterns_openai():
    pattern = next(p for p in PATTERNS if p.name == "OpenAI API Key")
    text = "Here is my secret sk-proj-abc1234567890abcdef1234567890abcdef12345678 and legacy sk-abcdef1234567890abcdef12"
    matches = pattern.find_matches(text)
    assert len(matches) == 2
    assert "sk-proj-abc" in matches[0][2]
    assert "sk-abcdef" in matches[1][2]


def test_patterns_aws_and_github():
    aws_pattern = next(p for p in PATTERNS if p.name == "AWS Access Key ID")
    gh_pattern = next(p for p in PATTERNS if p.name == "GitHub Token")

    text = "AWS: AKIAIOSFODNN7EXAMPLE, GitHub: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    aws_matches = aws_pattern.find_matches(text)
    gh_matches = gh_pattern.find_matches(text)

    assert len(aws_matches) == 1
    assert aws_matches[0][2] == "AKIAIOSFODNN7EXAMPLE"
    assert len(gh_matches) == 1
    assert gh_matches[0][2] == "ghp_1234567890abcdefghijklmnopqrstuvwxyz"


def test_patterns_email_and_ip():
    email_p = next(p for p in PATTERNS if p.name == "Email Address")
    ip_p = next(p for p in PATTERNS if p.name == "IPv4 Address")

    text = "Contact support@company.org or debug at 192.168.1.1"
    emails = email_p.find_matches(text)
    ips = ip_p.find_matches(text)

    assert len(emails) == 1
    assert emails[0][2] == "support@company.org"
    assert len(ips) == 1
    assert ips[0][2] == "192.168.1.1"


def test_patterns_jwt():
    jwt_p = next(p for p in PATTERNS if p.name == "JSON Web Token (JWT)")
    sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Authorization: Bearer {sample_jwt}"
    matches = jwt_p.find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == sample_jwt


def test_entropy_analyzer_true_positives():
    # Random high-entropy secret
    random_secret = "4aF9xK2mP9zL1qW7vB8"
    is_sec, score, reason = EntropyAnalyzer.is_secret_candidate(random_secret)
    assert is_sec is True
    assert score >= 4.0

    # Hex secret (32+ chars)
    hex_secret = "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"
    is_sec, score, reason = EntropyAnalyzer.is_secret_candidate(hex_secret)
    assert is_sec is True


def test_entropy_analyzer_false_positive_rejection():
    # Long English words / camelCase identifiers should NOT be flagged
    normal_words = [
        "https://api.github.com/v3/repos/owner/project/issues",
        "C:\\Users\\Developer\\AppData\\Local\\Programs\\Python",
        "AbstractSingletonProxyFactoryBean",
        "data-user-profile-widget-container",
        "Muvaffakiyetsizleştiricileştiriveremeyebileceklerimizdenmişsinizcesine",
    ]
    for word in normal_words:
        is_sec, score, reason = EntropyAnalyzer.is_secret_candidate(word)
        assert is_sec is False, f"False positive detected on: {word} ({reason})"


def test_masker_gaussian_and_dark_pill():
    img = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
    bboxes = [(20, 20, 60, 30)]

    blurred = RedactionMasker.apply_redaction(img, bboxes, RedactionStyle.GAUSSIAN_BLUR)
    assert blurred.size == (200, 100)

    pilled = RedactionMasker.apply_redaction(img, bboxes, RedactionStyle.DARK_PILL)
    assert pilled.size == (200, 100)
    # Check that pill area is dark slate
    pixel = pilled.getpixel((30, 35))
    assert pixel[0] == 15 and pixel[1] == 23 and pixel[2] == 42


def test_end_to_end_pipeline_with_ocr():
    from PIL import ImageFont
    # Create image with confidential text at standard desktop font size
    img = Image.new("RGB", (800, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=20)
    draw.text((30, 30), "Service Config:", font=font, fill=(0, 0, 0))
    draw.text((30, 80), "OpenAI: sk-proj-1234567890abcdef1234567890abcdef12345678", font=font, fill=(0, 0, 0))
    draw.text((30, 140), "Contact: devops@security.io", font=font, fill=(0, 0, 0))
    draw.text((30, 200), "Server IP: 192.168.1.100", font=font, fill=(0, 0, 0))

    pipeline = RedactionPipeline()
    redacted_img, targets = pipeline.process(img, style=RedactionStyle.GAUSSIAN_BLUR)

    assert len(targets) >= 3
    target_names = [t.name for t in targets]
    assert "OpenAI API Key" in target_names
    assert "Email Address" in target_names

    # Test copy as text with redaction
    sanitized_text = pipeline.copy_as_text(img, redact_secrets=True)
    assert "devops@security.io" not in sanitized_text
    assert "REDACTED" in sanitized_text


def test_patterns_contextual_tckn():
    p = next(p for p in PATTERNS if p.name == "Contextual Turkish ID (TCKN)")
    test_cases = [
        ("tc kimlik no: 12345678901", "12345678901"),
        ("TC No: 99988877766", "99988877766"),
        ("T.C. Kimlik No: 11111111111", "11111111111"),
        ("tckn: 12345678901", "12345678901"),
        ("kimlik no: 55544433322", "55544433322"),
        ("te49012345678", "49012345678"),
        ("t49012345678", "49012345678"),
        ("tc: 490 12345678", "490 12345678"),
        ("49012345678", "49012345678"),
    ]
    for text, expected_id in test_cases:
        matches = p.find_matches(text)
        assert len(matches) >= 1, f"Failed to match: {text}"
        assert expected_id in matches[0][2]


def test_patterns_passwords_multilingual_and_masked():
    p_kw = next(p for p in PATTERNS if p.name == "Password / Secret with Keyword")
    p_mask = next(p for p in PATTERNS if p.name == "Masked Password Input")

    samples_kw = [
        ("sifre: Gizli123!", "Gizli123!"),
        ("şifre: 123456", "123456"),
        ("şifre;876567889", "876567889"),
        ("password;secret_pass1", "secret_pass1"),
        ("parola; 12345678", "12345678"),
        ("parola: MySecretPassword", "MySecretPassword"),
        ("password: admin", "admin"),
        ("pass: Secret_99!", "Secret_99!"),
        ("pin: 4321", "4321"),
    ]
    for text, expected_val in samples_kw:
        matches = p_kw.find_matches(text)
        assert len(matches) == 1, f"Failed keyword match: {text}"
        assert matches[0][2] == expected_val

    # Masked password input (dots/asterisks)
    masked_samples = ["••••••••", "●●●●●●", "********"]
    for text in masked_samples:
        matches = p_mask.find_matches(text)
        assert len(matches) == 1, f"Failed masked match: {text}"


def test_entropy_standalone_passwords():
    # Real-world passwords should be identified as secrets
    real_passwords = ["Admin123!", "P@ssw0rd99", "Secret_2025!", "K1ng_2024!"]
    for pwd in real_passwords:
        is_sec, score, reason = EntropyAnalyzer.is_secret_candidate(pwd)
        assert is_sec is True, f"Failed to detect password: {pwd}"

    # Normal chat headers, usernames, timestamps and product words should NOT be flagged
    normal_words = [
        "RedactSnap",
        "Windows11",
        "CleanShot",
        "Development",
        "User1234",
        "Project2024",
        "Channel2025",
        "Ahmet1988",
        "Sprint42",
        "2024-11-05 14:30",
    ]
    for word in normal_words:
        is_sec, score, reason = EntropyAnalyzer.is_secret_candidate(word)
        assert is_sec is False, f"False positive on word: {word}"


def test_ocr_small_ui_text_preprocessing():
    # Test OCR on small, low-contrast browser address bar simulation
    img = Image.new("RGB", (480, 36), color=(241, 243, 244))
    draw = ImageDraw.Draw(img)
    draw.text((12, 10), "tc: 49012345678", fill=(80, 80, 80))

    pipeline = RedactionPipeline()
    redacted_img, targets = pipeline.process(img, style=RedactionStyle.GAUSSIAN_BLUR)

    assert len(targets) >= 1
    assert any("49012345678" in t.matched_text for t in targets)


def test_rapid_ocr_warmup():
    engine = RapidOCREngine()
    # Calling warmup should execute with no exceptions
    engine.warmup()
    assert engine.is_available is True


def test_redaction_worker_async(qapp):
    from redactsnap.redaction.worker import RedactionWorker

    img = Image.new("RGB", (300, 60), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "OpenAI: sk-proj-1234567890abcdef1234567890abcdef12345678", fill=(0, 0, 0))

    pipeline = RedactionPipeline()
    worker = RedactionWorker(scan_id=42, image=img, pipeline=pipeline)

    results = []

    def on_finished(scan_id, redacted_img, targets):
        results.append((scan_id, redacted_img, targets))

    worker.finished.connect(on_finished)
    worker.start()
    worker.wait(5000)
    qapp.processEvents()

    assert len(results) == 1
    scan_id, redacted_img, targets = results[0]
    assert scan_id == 42
    assert isinstance(redacted_img, Image.Image)
    assert len(targets) >= 1
