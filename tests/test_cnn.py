"""Tests for the CNN classification endpoint."""

import io
from unittest.mock import patch

from PIL import Image


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (224, 224), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_MOCK_PREDICTIONS = [
    {"label": "tabby cat", "confidence": 0.8234},
    {"label": "tiger cat", "confidence": 0.1012},
]


def test_classify_image(client, auth_headers):
    png = _make_png_bytes()
    with patch("app.models.cnn.router.classify_image", return_value=_MOCK_PREDICTIONS):
        resp = client.post(
            "/models/cnn/classify",
            headers=auth_headers,
            files={"file": ("cat.png", png, "image/png")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert data["predictions"][0]["label"] == "tabby cat"
    assert 0.0 <= data["predictions"][0]["confidence"] <= 1.0


def test_classify_non_image(client, auth_headers):
    resp = client.post(
        "/models/cnn/classify",
        headers=auth_headers,
        files={"file": ("doc.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_classify_invalid_top_k(client, auth_headers):
    png = _make_png_bytes()
    resp = client.post(
        "/models/cnn/classify?top_k=0",
        headers=auth_headers,
        files={"file": ("img.png", png, "image/png")},
    )
    assert resp.status_code == 400


def test_classify_requires_auth(client):
    png = _make_png_bytes()
    resp = client.post(
        "/models/cnn/classify",
        files={"file": ("img.png", png, "image/png")},
    )
    assert resp.status_code == 401
