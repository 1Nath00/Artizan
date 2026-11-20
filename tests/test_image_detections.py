import asyncio
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.datastructures import UploadFile
from sqlmodel import Session, SQLModel, create_engine

from app.auth.models import User
from app.categorias.models import Categoria
from app.images.models import Image
from app.images.service import (
    analyze_image,
    detect_objects,
    normalize_detections,
    persist_detections,
)


def test_normalize_detections_filters_translates_and_deduplicates():
    detections = normalize_detections(
        [
            {"clase": "chair", "confianza": 0.6, "bbox": [1, 2, 3, 4]},
            {"clase": "Chair", "confianza": 0.9, "bbox": [5, 6, 7, 8]},
            {"clase": "book", "confianza": 0.5, "bbox": [9, 10, 11, 12]},
            {"clase": "person", "confianza": 0.49, "bbox": [0, 0, 1, 1]},
            {"clase": "unknown-object", "confianza": 0.8, "bbox": [1, 1, 2, 2]},
        ]
    )

    assert detections == [
        {
            "clase_original": "Chair",
            "clase_es": "silla",
            "confianza": 0.9,
            "bbox": [5, 6, 7, 8],
        },
        {
            "clase_original": "unknown-object",
            "clase_es": None,
            "confianza": 0.8,
            "bbox": [1, 1, 2, 2],
        },
        {
            "clase_original": "book",
            "clase_es": "libro",
            "confianza": 0.5,
            "bbox": [9, 10, 11, 12],
        },
    ]


def test_normalize_detections_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="between 0 and 1"):
        normalize_detections(
            [{"clase": "chair", "confianza": 1.1, "bbox": [1, 2, 3, 4]}]
        )


def test_persist_detections_replaces_previous_results():
    image = SimpleNamespace(detecciones=[{"clase_original": "old"}])

    class Session:
        added = None
        committed = False

        def add(self, value):
            self.added = value

        def commit(self):
            self.committed = True

        def refresh(self, value):
            assert value is image

    session = Session()
    result = persist_detections(
        session,
        image,
        [{"clase": "cup", "confianza": 0.75, "bbox": [1, 2, 3, 4]}],
    )

    assert result == [
        {
            "clase_original": "cup",
            "clase_es": "taza",
            "confianza": 0.75,
            "bbox": [1, 2, 3, 4],
        }
    ]
    assert image.detecciones == result
    assert session.added is image
    assert session.committed


def test_analyze_image_persists_normalized_detections():
    image = SimpleNamespace(detecciones=None)
    session = SimpleNamespace()
    detections = [
        {"clase": "chair", "confianza": 0.9, "bbox": [1, 2, 3, 4]},
        {"clase": "person", "confianza": 0.3, "bbox": [0, 0, 1, 1]},
    ]

    with patch(
        "app.images.service.classify_image",
        return_value=[{"label": "Barroco", "confidence": 0.8}],
    ), patch(
        "app.images.service.detect_objects_from_bytes",
        return_value=detections,
    ), patch(
        "app.images.service.resolve_categoria_id_for_label",
        return_value=None,
    ), patch(
        "app.images.service._persist_image",
        return_value=image,
    ) as persist_image:
        result = asyncio.run(
            analyze_image(
                session,
                UploadFile(filename="art.png", file=io.BytesIO(b"image")),
                usuario_id=5,
            )
        )

    assert result == (image, [{"label": "Barroco", "confidence": 0.8}], detections)
    assert persist_image.call_args.kwargs["detecciones"] == [
        {
            "clase_original": "chair",
            "clase_es": "silla",
            "confianza": 0.9,
            "bbox": [1, 2, 3, 4],
        }
    ]


def test_image_detections_round_trip_through_json_column():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    detections = [
        {
            "clase_original": "chair",
            "clase_es": "silla",
            "confianza": 0.9,
            "bbox": [1, 2, 3, 4],
        }
    ]

    with Session(engine) as session:
        user = User(username="qa", email="qa@example.test", hashed_password="hash")
        category = Categoria(nombre="Barroco", slug="barroco")
        session.add_all([user, category])
        session.flush()
        image = Image(
            usuario_id=user.id,
            imagen_url="image.png",
            categoria_id=category.id,
            detecciones=detections,
        )
        session.add(image)
        session.commit()
        image_id = image.id

    with Session(engine) as session:
        stored_image = session.get(Image, image_id)

    assert stored_image is not None
    assert stored_image.detecciones == detections


def test_detect_objects_reads_local_uploads():
    with tempfile.TemporaryDirectory() as temp_dir:
        image_path = Path(temp_dir) / "image.png"
        image_path.write_bytes(b"image-bytes")
        with patch(
            "app.images.service.detect_objects_from_bytes",
            return_value=[],
        ) as detect_from_bytes:
            result = detect_objects(str(image_path))

    assert result == []
    detect_from_bytes.assert_called_once_with(b"image-bytes", conf=0.25)
