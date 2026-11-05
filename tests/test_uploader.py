"""
Unit tests for the Zero-Server Uploader and Config module.
"""

import pytest
from PIL import Image

from redactsnap.core.uploader import (
    ImgurUploader,
    S3Uploader,
    UploadResult,
    UploadProvider,
    UploadWorker,
)
from redactsnap.core.config import ConfigManager, RedactSnapConfig


def test_config_defaults():
    cfg = ConfigManager.load()
    assert cfg.default_provider in ("imgur", "s3")
    assert cfg.record_fps >= 10


def test_upload_result_dataclass():
    res = UploadResult(success=True, url="https://i.imgur.com/example.png")
    assert res.success is True
    assert "imgur.com" in res.url


def test_imgur_uploader_network_handling(monkeypatch):
    # Mock requests.post to simulate a successful Imgur response
    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "data": {
                    "link": "https://i.imgur.com/mock123.png"
                }
            }

    monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockResponse())

    img = Image.new("RGB", (100, 100), (255, 0, 0))
    res = ImgurUploader.upload(img, client_id="mock_id")
    assert res.success is True
    assert res.url == "https://i.imgur.com/mock123.png"


def test_upload_worker_thread(qapp, monkeypatch):
    class MockResponse:
        status_code = 200
        @staticmethod
        def json():
            return {"data": {"link": "https://i.imgur.com/thread123.png"}}

    monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockResponse())

    img = Image.new("RGB", (50, 50))
    worker = UploadWorker(img, provider=UploadProvider.IMGUR)

    results = []
    worker.upload_finished.connect(lambda r: results.append(r))
    worker.run()

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].url == "https://i.imgur.com/thread123.png"
