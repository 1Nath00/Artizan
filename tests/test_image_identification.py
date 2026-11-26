"""Pruebas del índice visual de pinturas."""

import io
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image
import pytest
from sqlmodel import select
import torch

from app.categorias.models import Categoria
from app.images import image_search
from app.images.identification_schemas import (
    IdentificarImagenResponse,
    PinturaIdentificada,
)
from app.pinturas.models import Pintura


def _png_bytes(width: int = 16, height: int = 16) -> bytes:
    image = Image.new("RGB", (width, height), "red")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_prepare_image_converts_to_rgb_and_limits_dimensions():
    image = Image.new("RGBA", (2048, 1024), (255, 0, 0, 255))

    prepared = image_search.preparar_imagen(image)

    assert prepared.mode == "RGB"
    assert prepared.size == (1024, 512)


def test_cloudinary_url_adds_lightweight_transformation_once():
    url = "https://res.cloudinary.com/demo/image/upload/v1/obra.jpg"

    transformed = image_search.cloudinary_lightweight_url(url)

    assert transformed == (
        "https://res.cloudinary.com/demo/image/upload/w_448,c_limit/v1/obra.jpg"
    )
    assert image_search.cloudinary_lightweight_url(transformed) == transformed
    direct = "https://res.cloudinary.com/demo/image/upload/artizan/obra.jpg"
    assert "/upload/w_448,c_limit/artizan/obra.jpg" in image_search.cloudinary_lightweight_url(
        direct
    )
    assert image_search.cloudinary_lightweight_url("https://example.com/obra.jpg") == (
        "https://example.com/obra.jpg"
    )


def test_embeddings_use_cls_token_and_l2_normalization():
    class FakeProcessor:
        def __call__(self, images, return_tensors):
            assert return_tensors == "pt"
            return {"pixel_values": torch.zeros((len(images), 3, 2, 2))}

    class FakeOutput:
        def __init__(self, batch_size):
            hidden = torch.zeros((batch_size, 2, 2))
            hidden[:, 0, :] = torch.tensor([3.0, 4.0])
            self.last_hidden_state = hidden

    model = Mock(side_effect=lambda **_: FakeOutput(2))
    images = [Image.new("RGB", (2, 2)), Image.new("RGB", (2, 2))]
    with patch.object(image_search, "get_image_model", return_value=model), patch.object(
        image_search, "get_image_processor", return_value=FakeProcessor()
    ), patch.object(
        image_search, "get_image_device", return_value=torch.device("cpu")
    ):
        result = image_search.embeddings_imagenes(images)

    assert np.allclose(result, [[0.6, 0.8], [0.6, 0.8]])


def test_image_collection_rejects_vectors_from_another_model(monkeypatch):
    client = Mock()
    collection = Mock(metadata={"hnsw:space": "cosine", "modelo": "otro-modelo"})
    client.get_collection.return_value = collection
    monkeypatch.setattr(
        "chromadb.PersistentClient",
        Mock(return_value=client),
    )
    image_search.get_image_collection.cache_clear()

    try:
        with pytest.raises(
            image_search.ImageSearchConfigurationError,
            match="--reset",
        ):
            image_search.get_image_collection()
    finally:
        image_search.get_image_collection.cache_clear()


def test_upsert_uses_only_painting_id_and_category_metadata():
    collection = Mock()
    rows = [{"id": 12, "categoria_id": 3, "url": "https://example.com/obra.jpg"}]
    images = [Image.new("RGB", (4, 4))]
    with patch.object(image_search, "embeddings_imagenes", return_value=[[0.1, 0.2]]), patch.object(
        image_search, "get_image_collection", return_value=collection
    ):
        assert image_search.upsert_pinturas(rows, images) == 1

    collection.upsert.assert_called_once_with(
        ids=["12"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"categoria_id": 3}],
    )


def test_obtener_pintura_maps_configured_database_columns(db_session):
    categoria = db_session.exec(
        select(Categoria).where(Categoria.slug == "cubismo")
    ).one()
    pintura = Pintura(
        autor="Pablo Picasso",
        nombre="Obra",
        año=1907,
        categoria_id=categoria.id,
        url_imagen="https://res.cloudinary.com/demo/obra.jpg",
        filename_original="obra-1907.jpg",
        descripcion="Descripción",
    )
    db_session.add(pintura)
    db_session.commit()
    db_session.refresh(pintura)

    result = image_search.obtener_pinturas_por_ids(db_session, [pintura.id])

    assert result[pintura.id].model_dump() == {
        "id": pintura.id,
        "imagen_url": pintura.url_imagen,
        "autor": "Pablo Picasso",
        "anio": 1907,
        "descripcion": "Descripción",
        "categoria_id": categoria.id,
    }


def test_identification_state_uses_configured_thresholds(db_session):
    pintura = PinturaIdentificada(
        id=12,
        imagen_url="https://example.com/obra.jpg",
        autor="Autora",
        anio=1907,
        descripcion="Obra",
        categoria_id=3,
    )
    with patch.object(image_search, "embedding_imagen", return_value=[0.1]), patch.object(
        image_search,
        "buscar_similares",
        return_value=[image_search.ImageMatch(pintura_id=12, score=0.70)],
    ), patch.object(
        image_search,
        "obtener_pinturas_por_ids",
        return_value={12: pintura},
    ), patch.object(image_search, "abrir_imagen", return_value=Image.new("RGB", (2, 2))):
        response = image_search.identificar_imagen(db_session, b"image")

    assert response.estado == "dudosa"
    assert response.pintura == pintura
    assert [candidate.id for candidate in response.candidatos] == [12]


def test_identificar_endpoint_validates_file_type_and_size(client):
    invalid_type = client.post(
        "/identificar",
        files={"file": ("obra.txt", b"not-an-image", "text/plain")},
    )
    assert invalid_type.status_code == 400
    assert "JPEG, PNG o WebP" in invalid_type.json()["detail"]

    oversized = client.post(
        "/identificar",
        files={"file": ("obra.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert oversized.status_code == 413


def test_identificar_endpoint_returns_public_cloudinary_data(client):
    expected = IdentificarImagenResponse(
        estado="encontrada",
        score=0.93,
        pintura=PinturaIdentificada(
            id=12,
            imagen_url="https://res.cloudinary.com/demo/obra.jpg",
            autor="Autora",
            anio=1907,
            descripcion="Obra",
            categoria_id=3,
        ),
        candidatos=[],
    )
    with patch(
        "app.images.router.image_search.identificar_imagen",
        return_value=expected,
    ):
        response = client.post(
            "/identificar",
            files={"file": ("obra.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["pintura"]["imagen_url"].startswith("https://res.cloudinary.com/")
    assert response.json()["pintura"]["anio"] == 1907
