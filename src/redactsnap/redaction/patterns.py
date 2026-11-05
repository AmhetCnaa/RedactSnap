"""
Pattern definitions and regex catalog for sensitive data detection in RedactSnap.
Categorizes secrets and PII (API Keys, Tokens, Credentials, Financials, Network, PII).
"""

import re
from typing import Dict, List, Optional, Tuple


def luhn_checksum_valid(card_number: str) -> bool:
    """Validates credit card number using Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"\D", "", card_number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


def tckn_valid(tckn: str) -> bool:
    """Validates Turkish Citizen Identity Number (TCKN)."""
    digits = [int(d) for d in re.sub(r"\D", "", tckn)]
    if len(digits) != 11 or digits[0] == 0:
        return False
    d1_to_9_sum = sum(digits[:9])
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    d10 = (odd_sum * 7 - even_sum) % 10
    d11 = (d1_to_9_sum + digits[9]) % 10
    return digits[9] == d10 and digits[10] == d11


class SecretPattern:
    def __init__(
        self,
        name: str,
        category: str,
        regex: str,
        validator: Optional[callable] = None,
        flags: int = 0
    ):
        self.name = name
        self.category = category
        self.regex = re.compile(regex, flags)
        self.validator = validator

    def find_matches(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Returns list of (start_index, end_index, matched_secret_text).
        If capture groups exist, returns group 1 (or full match).
        """
        matches = []
        for match in self.regex.finditer(text):
            # If pattern has capture group (e.g. key: <value>), use group 1
            if match.lastindex and match.lastindex >= 1:
                start = match.start(1)
                end = match.end(1)
                secret = match.group(1)
            else:
                start = match.start()
                end = match.end()
                secret = match.group()

            if self.validator is not None:
                if not self.validator(secret):
                    continue

            matches.append((start, end, secret))
        return matches


PATTERNS: List[SecretPattern] = [
    # --------------------------------------------------------------------------
    # AI & Cloud API Keys
    # --------------------------------------------------------------------------
    SecretPattern(
        name="OpenAI API Key",
        category="API_KEY",
        regex=r"\b(sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{40,}|sk-admin-[a-zA-Z0-9_\-]{40,})\b"
    ),
    SecretPattern(
        name="AWS Access Key ID",
        category="CLOUD_CREDENTIAL",
        regex=r"\b((?:AKIA|ASIA|AROA)[0-9A-Z]{16})\b"
    ),
    SecretPattern(
        name="AWS Secret Key",
        category="CLOUD_CREDENTIAL",
        regex=r"(?i)\b(?:aws_secret_access_key|aws_secret_key|secret_access_key)\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})[\"']?"
    ),
    SecretPattern(
        name="GitHub Token",
        category="API_KEY",
        regex=r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}|github_pat_[A-Za-z0-9_]{82})\b"
    ),
    SecretPattern(
        name="Google Cloud / Gemini API Key",
        category="API_KEY",
        regex=r"\b(AIza[0-9A-Za-z\-_]{35})\b"
    ),
    SecretPattern(
        name="Slack Token",
        category="API_KEY",
        regex=r"\b(xox[baprs]-[0-9A-Za-z\-]{10,48})\b"
    ),
    SecretPattern(
        name="Stripe Secret Key",
        category="FINANCIAL_KEY",
        regex=r"\b((?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,})\b"
    ),
    SecretPattern(
        name="Anthropic API Key",
        category="API_KEY",
        regex=r"\b(sk-ant-[a-zA-Z0-9_\-]{30,})\b"
    ),
    SecretPattern(
        name="Hugging Face Token",
        category="API_KEY",
        regex=r"\b(hf_[a-zA-Z0-9]{34,})\b"
    ),

    # --------------------------------------------------------------------------
    # Authentication & Cryptography
    # --------------------------------------------------------------------------
    SecretPattern(
        name="JSON Web Token (JWT)",
        category="TOKEN",
        regex=r"\b(eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,})\b"
    ),
    SecretPattern(
        name="Private Key Header",
        category="PRIVATE_KEY",
        regex=r"(-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP)?\s?PRIVATE KEY[^-]*-----)"
    ),
    SecretPattern(
        name="Generic Password in Config",
        category="PASSWORD",
        regex=r"(?i)\b(?:password|passwd|secret|api_key|apikey|auth_token|bearer)\s*[:=]\s*[\"']?([^\s\"']{8,})[\"']?"
    ),

    # --------------------------------------------------------------------------
    # Personal & Financial PII
    # --------------------------------------------------------------------------
    SecretPattern(
        name="Email Address",
        category="PII",
        regex=r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
    ),
    SecretPattern(
        name="Credit Card Number",
        category="FINANCIAL",
        regex=r"\b(?:\d{4}[ -]?){3}\d{4}\b|\b\d{4}[ -]?\d{6}[ -]?\d{5}\b",
        validator=luhn_checksum_valid
    ),
    SecretPattern(
        name="IBAN",
        category="FINANCIAL",
        regex=r"\b([A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7,26})\b"
    ),
    SecretPattern(
        name="Turkish Citizen ID (TCKN)",
        category="PII",
        regex=r"\b([1-9][0-9]{10})\b",
        validator=tckn_valid
    ),

    # --------------------------------------------------------------------------
    # Network Infrastructure
    # --------------------------------------------------------------------------
    SecretPattern(
        name="IPv4 Address",
        category="NETWORK",
        regex=r"\b((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b"
    ),
]
