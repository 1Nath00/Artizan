"""Tests for the images module."""

import io
from unittest.mock import patch

from PIL import Image


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_image(client, auth_headers):
    png = _make_png_bytes()
    resp = client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("test.png", png, "image/png")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_name"] == "test.png"
    assert data["content_type"] == "image/png"
    assert "url" in data


def test_upload_invalid_extension(client, auth_headers):
    resp = client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("script.exe", b"fake", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_analyze_failure_does_not_expose_exception(client, auth_headers):
    with patch(
        "app.images.router.service.analyze_image",
        side_effect=RuntimeError("private /internal/image failure"),
    ):
        resp = client.post(
            "/images/analyze",
            headers=auth_headers,
            files={"file": ("test.png", _make_png_bytes(), "image/png")},
        )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Could not process image."}
    assert "private /internal/image failure" not in resp.text


def test_detect_failure_does_not_expose_exception(client, auth_headers):
    upload = client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("detect.png", _make_png_bytes(), "image/png")},
    )
    image_id = upload.json()["id"]

    with patch(
        "app.images.router.service.detect_objects",
        side_effect=RuntimeError("private /internal/image failure"),
    ):
        resp = client.post(f"/images/{image_id}/detect", headers=auth_headers)

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Could not process the stored image."}
    assert "private /internal/image failure" not in resp.text


def test_list_images(client, auth_headers):
    png = _make_png_bytes()
    client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("a.png", png, "image/png")},
    )
    resp = client.get("/images/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_get_image(client, auth_headers):
    png = _make_png_bytes()
    upload = client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("b.png", png, "image/png")},
    )
    image_id = upload.json()["id"]
    resp = client.get(f"/images/{image_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == image_id


def test_get_image_not_found(client, auth_headers):
    resp = client.get("/images/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_image(client, auth_headers):
    png = _make_png_bytes()
    upload = client.post(
        "/images/upload",
        headers=auth_headers,
        files={"file": ("c.png", png, "image/png")},
    )
    image_id = upload.json()["id"]
    resp = client.delete(f"/images/{image_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/images/{image_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_images_require_auth(client):
    resp = client.get("/images/")
    assert resp.status_code == 401
