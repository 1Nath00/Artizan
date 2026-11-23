"""Tests for the images module."""

import io
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import Image
from app.images.models import Image as StoredImage


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
    assert data["id"] is not None
    assert data["imagen_url"]
    assert data["estado"] == "pendiente"
    assert data["confianza"] is None


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


def test_list_images_returns_newest_first(client, auth_headers, db_session):
    png = _make_png_bytes()
    image_ids = []
    for filename in ("older.png", "newer.png"):
        response = client.post(
            "/images/upload",
            headers=auth_headers,
            files={"file": (filename, png, "image/png")},
        )
        image_ids.append(response.json()["id"])

    older = db_session.get(StoredImage, image_ids[0])
    newer = db_session.get(StoredImage, image_ids[1])
    newer.created_at = datetime.now(timezone.utc)
    older.created_at = newer.created_at - timedelta(days=1)
    db_session.commit()

    response = client.get("/images/", headers=auth_headers)

    assert response.status_code == 200
    assert [image["id"] for image in response.json()] == [image_ids[1], image_ids[0]]


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


def _analyze_with_mock_predictions(client, auth_headers, predictions):
    with patch("app.images.service.classify_image", return_value=predictions), patch(
        "app.images.service.detect_objects_from_bytes", return_value=[]
    ):
        return client.post(
            "/images/analyze",
            headers=auth_headers,
            files={"file": ("obra.png", _make_png_bytes(), "image/png")},
        )


def _get_categoria_id(db_session, slug):
    from sqlmodel import select

    from app.categorias.models import Categoria

    return db_session.exec(select(Categoria).where(Categoria.slug == slug)).first().id


def test_analyze_persists_cubismo_categoria_and_confianza(client, auth_headers, db_session):
    resp = _analyze_with_mock_predictions(
        client,
        auth_headers,
        [{"label": "Cubismo", "confidence": 0.9134}, {"label": "Barroco", "confidence": 0.0866}],
    )
    assert resp.status_code == 201
    image_id = resp.json()["image_id"]

    detail = client.get(f"/images/{image_id}", headers=auth_headers).json()
    assert detail["categoria_id"] == _get_categoria_id(db_session, "cubismo")
    assert detail["confianza"] == 0.9134
    assert detail["estado"] == "clasificada"


def test_analyze_persists_barroco_categoria_and_confianza(client, auth_headers, db_session):
    resp = _analyze_with_mock_predictions(
        client,
        auth_headers,
        [{"label": "Barroco", "confidence": 0.7712}, {"label": "Cubismo", "confidence": 0.2288}],
    )
    assert resp.status_code == 201
    image_id = resp.json()["image_id"]

    detail = client.get(f"/images/{image_id}", headers=auth_headers).json()
    assert detail["categoria_id"] == _get_categoria_id(db_session, "barroco")
    assert detail["confianza"] == 0.7712


def test_analyze_unknown_label_persists_without_categoria(client, auth_headers):
    resp = _analyze_with_mock_predictions(
        client, auth_headers, [{"label": "tabby cat", "confidence": 0.99}]
    )
    assert resp.status_code == 201
    image_id = resp.json()["image_id"]

    detail = client.get(f"/images/{image_id}", headers=auth_headers).json()
    assert detail["categoria_id"] is None
    assert detail["confianza"] is None
    assert detail["titulo"] == "tabby cat"
