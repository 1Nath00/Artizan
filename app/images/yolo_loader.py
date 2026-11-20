from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_DIR / "yolo11n.pt"


class YoloModelLoadError(RuntimeError):
    """Error descriptivo al resolver o cargar el modelo YOLO."""


_model: Any = None
_model_lock = threading.Lock()


def resolve_yolo_model_path() -> Path:
    configured_path = os.getenv("YOLO_MODEL_PATH", "").strip()
    model_path = (
        Path(configured_path).expanduser() if configured_path else DEFAULT_MODEL_PATH
    )
    if not model_path.is_absolute():
        model_path = PROJECT_DIR / model_path
    model_path = model_path.resolve()

    if not model_path.is_file():
        raise YoloModelLoadError(
            "Modelo YOLO no encontrado en "
            f"{model_path}. Incluya yolo11n.pt en el despliegue o configure "
            "YOLO_MODEL_PATH."
        )
    return model_path


def get_yolo_model() -> Any:
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        model_path = resolve_yolo_model_path()
        try:
            from ultralytics import YOLO

            _model = YOLO(str(model_path))
        except Exception as exc:
            raise YoloModelLoadError(
                f"No se pudo cargar el modelo YOLO desde: {model_path}"
            ) from exc
        return _model
