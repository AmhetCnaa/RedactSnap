"""
Configuration manager for RedactSnap preferences and credentials.
Persists settings locally in user home directory under ~/.redactsnap/config.json.
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class RedactSnapConfig:
    default_provider: str = "imgur"
    imgur_client_id: str = "546c25a59c58ad7"
    s3_endpoint_url: str = ""
    s3_public_base_url: str = ""
    s3_auth_token: str = ""
    default_preset: str = "obsidian"
    auto_redact_default: bool = True
    default_padding: int = 48
    record_fps: int = 30
    record_format: str = "gif"


class ConfigManager:
    """Manages loading and saving user configuration to disk."""

    CONFIG_DIR = os.path.expanduser("~/.redactsnap")
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

    @classmethod
    def load(cls) -> RedactSnapConfig:
        """Loads configuration from JSON file or returns defaults."""
        if not os.path.exists(cls.CONFIG_PATH):
            return RedactSnapConfig()

        try:
            with open(cls.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RedactSnapConfig(**data)
        except Exception:
            return RedactSnapConfig()

    @classmethod
    def save(cls, config: RedactSnapConfig):
        """Saves configuration to JSON file."""
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        try:
            with open(cls.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2)
        except Exception as e:
            print(f"[RedactSnap] Failed to save config: {e}")
