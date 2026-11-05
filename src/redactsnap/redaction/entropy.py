"""
Shannon Entropy Calculator and heuristic analyzer for detecting high-entropy secrets
(random passwords, database keys, session hashes, bearer tokens) with minimal false positives.
"""

import math
import re
from collections import Counter
from typing import List, Tuple, Optional


class EntropyAnalyzer:
    """
    Computes information entropy H(X) and applies syntactic filters to distinguish
    true random secrets from natural language text, URLs, paths, and code identifiers.
    """

    # Common prefixes/patterns to safely ignore
    IGNORE_PATTERNS = [
        re.compile(r"^https?://", re.IGNORECASE),
        re.compile(r"^[a-zA-Z]:\\", re.IGNORECASE),  # Windows path
        re.compile(r"^/[a-zA-Z0-9_\-./]+$"),         # Unix path
        re.compile(r"^[a-zA-Z0-9_\-]+(\.[a-zA-Z0-9_\-]+)+$"),  # Domain name or package
    ]

    @staticmethod
    def calculate_entropy(text: str) -> float:
        """
        Calculates Shannon Entropy H(X) in bits per character.
        H(X) = -sum(P(x) * log2(P(x)))
        """
        if not text:
            return 0.0

        length = len(text)
        counts = Counter(text)
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    @classmethod
    def is_secret_candidate(cls, token: str) -> Tuple[bool, float, str]:
        """
        Analyzes a single token to determine if it is a high-entropy secret.

        Returns:
            (is_secret, entropy_score, reason)
        """
        token = token.strip(" '\"`(),;:[]{}<>")
        length = len(token)

        # Must meet minimum length threshold
        if length < 8:
            return False, 0.0, "Too short (< 8 chars)"

        # Check ignored structures (URLs, paths, namespaces)
        for pattern in cls.IGNORE_PATTERNS:
            if pattern.search(token):
                return False, 0.0, "Matched ignore pattern (URL/Path)"

        # Avoid snake_case or kebab-case identifiers with repetitive short words
        if "-" in token or "_" in token:
            parts = re.split(r"[-_]", token)
            # If composed of many regular words (e.g. data-user-profile-widget)
            if all(len(p) <= 10 and p.isalpha() for p in parts if p):
                return False, 0.0, "Hyphenated/Underscored identifier"

        entropy = cls.calculate_entropy(token)

        # Ignore purely alphabetic tokens (natural language words in English, Turkish, German, etc.)
        if token.isalpha():
            return False, entropy, "Pure alphabetic word (Natural Language)"

        has_lower = bool(re.search(r"[a-z]", token))
        has_upper = bool(re.search(r"[A-Z]", token))
        has_digit = bool(re.search(r"[0-9]", token))
        has_special = bool(re.search(r"[^a-zA-Z0-9]", token))

        char_classes = sum([has_lower, has_upper, has_digit, has_special])

        # 1. Hexadecimal hash / secret (e.g., 32+ hex characters: MD5, SHA, secret key)
        is_hex = bool(re.fullmatch(r"[0-9a-fA-F]+", token))
        if is_hex and length >= 32 and has_digit:
            # Theoretical max entropy for 16 symbols is 4.0
            if entropy >= 3.4:
                return True, entropy, "High-entropy Hex secret (>=32 hex)"

        # 2. General high-entropy token (Alphanumeric/Base64)
        # Must have digits and at least 3 character classes (e.g., upper + lower + digit)
        if has_digit and char_classes >= 3:
            if length >= 16 and entropy >= 3.8:
                return True, entropy, "High-entropy mixed token (>=16 chars, H>=3.8)"
            elif length >= 24 and entropy >= 3.6:
                return True, entropy, "High-entropy mixed token (>=24 chars, H>=3.6)"

        # 3. Base64-like token with padding or standard charset
        if re.fullmatch(r"[A-Za-z0-9+/=_-]+", token) and has_digit and (has_lower or has_upper):
            if length >= 24 and entropy >= 3.9:
                return True, entropy, "High-entropy Base64 token"

        # 4. Typical Standalone Password Pattern (8-15 chars, mixed classes e.g. Admin123!, P@ssw0rd99)
        # Requires at least one special character to avoid false positives on usernames/headers like Project2024
        if 8 <= length < 16:
            if has_digit and has_special and (has_lower or has_upper) and char_classes >= 3:
                return True, entropy, f"Password-like token (classes={char_classes}, H={entropy:.2f})"

        return False, entropy, "Normal text distribution"

    @classmethod
    def scan_text(cls, text: str) -> List[Tuple[int, int, str, float, str]]:
        """
        Tokenizes text and finds all high-entropy secret segments.
        Returns: [(start_idx, end_idx, token, entropy, reason), ...]
        """
        results = []
        # Split on whitespace and punctuation boundaries (including URL query delimiters ? and &)
        for match in re.finditer(r"[^\s:=,;\"'<>(){}\[\]?&]+", text):
            token = match.group()
            is_secret, entropy, reason = cls.is_secret_candidate(token)
            if is_secret:
                results.append((match.start(), match.end(), token, entropy, reason))
        return results
