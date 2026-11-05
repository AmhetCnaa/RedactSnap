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
