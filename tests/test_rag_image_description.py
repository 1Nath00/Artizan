from unittest.mock import patch

import pytest

from app.models.rag import service


def test_image_description_messages_separate_visual_data_and_context():
    messages = service.build_image_description_messages(
        "Cubismo",
        0.82,
        [{"clase_es": "silla"}],
        [{"filename": "cubismo.txt", "text": "El estilo usa planos.", "chunk": 0}],
    )

    assert "DATOS DE LA IMAGEN" in messages[1]["content"]
    assert "Objetos detectados (pistas visuales): silla" in messages[1]["content"]
    assert "CONTEXTO" in messages[1]["content"]
    assert "[1] El estilo usa planos." in messages[1]["content"]
    assert "No uses los datos visuales para completar información histórica ausente." in messages[0]["content"]


def test_describe_image_requires_style_and_preserves_exact_insufficient_answer():
    with patch("app.models.rag.service.retrieve") as retrieve:
        with pytest.raises(service.InsufficientContextError) as error:
            service.describe_image(None, None, [])

    assert str(error.value) == service.INSUFFICIENT_CONTEXT_ANSWER
    retrieve.assert_not_called()


def test_describe_image_rejects_insufficient_answer_from_model():
    hits = [{"filename": "barroco.txt", "text": "El Barroco usa claroscuros."}]
    with patch("app.models.rag.service.retrieve", return_value=hits), patch(
        "app.models.rag.service._generate_answer",
        return_value=(service.INSUFFICIENT_CONTEXT_ANSWER, 0.01),
    ):
        with pytest.raises(service.InsufficientContextError):
            service.describe_image("Barroco", 0.8, [])


def test_describe_image_adds_low_confidence_caution_and_requires_citations():
    hits = [{"filename": "barroco.txt", "text": "El Barroco usa claroscuros."}]
    with patch("app.models.rag.service.retrieve", return_value=hits), patch(
        "app.models.rag.service._generate_answer",
        return_value=("El Barroco emplea claroscuros [1].", 0.01),
    ):
        result = service.describe_image("Barroco", 0.55, [])

    assert result["answer"].startswith(service.LOW_CONFIDENCE_CAUTION)
    assert "[1]" in result["answer"]


def test_describe_image_rejects_out_of_range_citations():
    hits = [{"filename": "barroco.txt", "text": "El Barroco usa claroscuros."}]
    with patch("app.models.rag.service.retrieve", return_value=hits), patch(
        "app.models.rag.service._generate_answer",
        return_value=("El Barroco emplea claroscuros [2].", 0.01),
    ):
        with pytest.raises(service.RAGError, match="valid context citations"):
            service.describe_image("Barroco", 0.8, [])
