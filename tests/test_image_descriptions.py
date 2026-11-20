from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.images.router import generate_image_description
from app.models.rag import service as rag_service


def _session_for_image(detecciones=None):
    image = SimpleNamespace(
        id=17,
        usuario_id=5,
        imagen_url="uploads/art.png",
        categoria_id=3,
        confianza=0.82,
        descripcion="Descripción anterior",
        detecciones=detecciones,
    )
    category = SimpleNamespace(id=3, nombre="Barroco")

    class Session:
        def __init__(self):
            self.commits = 0

        def get(self, model, model_id):
            if model.__name__ == "Image":
                return image if model_id == image.id else None
            if model.__name__ == "Categoria":
                return category if model_id == category.id else None
            return None

        def add(self, value):
            assert value is image

        def commit(self):
            self.commits += 1

        def refresh(self, value):
            assert value is image

    return image, Session()


def test_image_description_saves_success_and_reuses_persisted_detections():
    existing_detections = [
        {
            "clase_original": "chair",
            "clase_es": "silla",
            "confianza": 0.81,
            "bbox": [1, 2, 3, 4],
        }
    ]
    image, session = _session_for_image(existing_detections)
    generated = "El Barroco utiliza contrastes de luz [1]."

    with patch("app.images.router.service.detect_objects") as detect, patch(
        "app.images.router.rag_service.describe_image",
        return_value={"answer": generated},
    ) as describe:
        result = generate_image_description(
            image_id=image.id,
            session=session,
            current_user=SimpleNamespace(id=image.usuario_id),
        )

    detect.assert_not_called()
    describe.assert_called_once_with(
        style="Barroco",
        confidence=0.82,
        detections=existing_detections,
    )
    assert result.descripcion == generated
    assert result.detecciones == existing_detections


def test_image_description_preserves_previous_text_on_insufficient_context():
    image, session = _session_for_image()
    detections = [{"clase": "cup", "confianza": 0.8, "bbox": [1, 2, 3, 4]}]

    with patch("app.images.router.service.detect_objects", return_value=detections), patch(
        "app.images.router.rag_service.describe_image",
        side_effect=rag_service.InsufficientContextError(
            rag_service.INSUFFICIENT_CONTEXT_ANSWER
        ),
    ):
        with pytest.raises(HTTPException) as error:
            generate_image_description(
                image_id=image.id,
                session=session,
                current_user=SimpleNamespace(id=image.usuario_id),
            )

    assert error.value.status_code == 422
    assert image.descripcion == "Descripción anterior"
    assert image.detecciones[0]["clase_es"] == "taza"
    assert session.commits == 1


def test_image_description_preserves_previous_text_on_rag_failure():
    image, session = _session_for_image(
        [{"clase_original": "cup", "clase_es": "taza", "confianza": 0.8, "bbox": []}]
    )

    with patch(
        "app.images.router.rag_service.describe_image",
        side_effect=rag_service.RAGError("Ollama is unavailable"),
    ):
        with pytest.raises(HTTPException) as error:
            generate_image_description(
                image_id=image.id,
                session=session,
                current_user=SimpleNamespace(id=image.usuario_id),
            )

    assert error.value.status_code == 503
    assert image.descripcion == "Descripción anterior"
    assert session.commits == 0


def test_image_description_requires_image_owner():
    image, session = _session_for_image()

    with patch("app.images.router.service.detect_objects") as detect:
        with pytest.raises(HTTPException) as error:
            generate_image_description(
                image_id=image.id,
                session=session,
                current_user=SimpleNamespace(id=999),
            )

    assert error.value.status_code == 403
    detect.assert_not_called()
    assert image.descripcion == "Descripción anterior"
