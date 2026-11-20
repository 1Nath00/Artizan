from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.images import yolo_loader


@pytest.fixture(autouse=True)
def reset_yolo_loader(monkeypatch):
    monkeypatch.delenv("YOLO_MODEL_PATH", raising=False)
    yolo_loader._model = None
    yield
    yolo_loader._model = None


def test_resolve_yolo_model_path_defaults_to_project_file():
    with patch.object(Path, "is_file", return_value=True):
        path = yolo_loader.resolve_yolo_model_path()

    assert path == (yolo_loader.PROJECT_DIR / "yolo11n.pt").resolve()


def test_resolve_yolo_model_path_reports_missing_file(tmp_path):
    missing_path = tmp_path / "missing.pt"

    with patch.dict("os.environ", {"YOLO_MODEL_PATH": str(missing_path)}):
        with pytest.raises(yolo_loader.YoloModelLoadError, match="Modelo YOLO no encontrado"):
            yolo_loader.resolve_yolo_model_path()


def test_get_yolo_model_loads_and_reuses_model(tmp_path):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"weights")
    loaded_model = Mock()

    with patch.dict("os.environ", {"YOLO_MODEL_PATH": str(model_path)}), patch(
        "ultralytics.YOLO", return_value=loaded_model
    ) as yolo:
        assert yolo_loader.get_yolo_model() is loaded_model
        assert yolo_loader.get_yolo_model() is loaded_model

    yolo.assert_called_once_with(str(model_path.resolve()))
