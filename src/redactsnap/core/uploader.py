"""
Zero-Server Instant Link Sharing for RedactSnap.
Supports anonymous Imgur uploads and custom Cloudflare R2 / AWS S3 / MinIO buckets.
"""

import io
import time
import base64
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
from PIL import Image
import requests

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class UploadProvider(Enum):
    IMGUR = "imgur"
    S3_COMPATIBLE = "s3"


@dataclass
class UploadResult:
    success: bool
    url: str = ""
    error_message: str = ""


class ImgurUploader:
    """Anonymous image uploader via Imgur v3 API (Zero login required)."""

    DEFAULT_CLIENT_ID = "546c25a59c58ad7"
    API_URL = "https://api.imgur.com/3/image"

    @classmethod
    def upload(cls, image: Image.Image, client_id: Optional[str] = None) -> UploadResult:
        cid = client_id or cls.DEFAULT_CLIENT_ID

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        headers = {
            "Authorization": f"Client-ID {cid}"
        }
        files = {
            "image": ("screenshot.png", img_bytes, "image/png")
        }

        try:
            resp = requests.post(cls.API_URL, headers=headers, files=files, timeout=12)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                link = data.get("link", "")
                return UploadResult(success=True, url=link)
            else:
                return UploadResult(
                    success=False,
                    error_message=f"Imgur upload failed (HTTP {resp.status_code}): {resp.text[:120]}"
                )
        except Exception as e:
            return UploadResult(success=False, error_message=str(e))


class S3Uploader:
    """Uploads to Cloudflare R2, AWS S3, or MinIO buckets using direct PUT or presigned URLs."""

    @classmethod
    def upload(
        cls,
        image: Image.Image,
        endpoint_url: str,
        public_base_url: str,
        auth_token: Optional[str] = None
    ) -> UploadResult:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"redactsnap_{timestamp}.png"

        target_url = f"{endpoint_url.rstrip('/')}/{filename}"
        headers = {"Content-Type": "image/png"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            resp = requests.put(target_url, data=img_bytes, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                public_url = f"{public_base_url.rstrip('/')}/{filename}"
                return UploadResult(success=True, url=public_url)
            else:
                return UploadResult(
                    success=False,
                    error_message=f"S3 PUT upload failed (HTTP {resp.status_code}): {resp.text[:120]}"
                )
        except Exception as e:
            return UploadResult(success=False, error_message=str(e))


class UploadWorker(QThread):
    """Background worker for non-blocking UI uploads."""

    upload_finished = pyqtSignal(UploadResult)

    def __init__(
        self,
        image: Image.Image,
        provider: UploadProvider = UploadProvider.IMGUR,
        config: Optional[Dict] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.image = image
        self.provider = provider
        self.config = config or {}

    def run(self):
        if self.provider == UploadProvider.IMGUR:
            client_id = self.config.get("imgur_client_id")
            res = ImgurUploader.upload(self.image, client_id=client_id)
        elif self.provider == UploadProvider.S3_COMPATIBLE:
            endpoint = self.config.get("endpoint_url", "")
            public_base = self.config.get("public_base_url", "")
            token = self.config.get("auth_token")
            res = S3Uploader.upload(self.image, endpoint, public_base, token)
        else:
            res = UploadResult(success=False, error_message="Unknown upload provider")

        self.upload_finished.emit(res)
