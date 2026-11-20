"""Carga centralizada y reutilizable del modelo Keras de clasificación."""

from __future__ import annotations

import os
import tempfile
import threading
from functools import lru_cache
from typing import Any


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "cnn",
    "modelo_pinturas_gridsearch.keras",
)

MODEL_STORAGE_ENV = "MODEL_STORAGE"
RAILWAY_REQUIRED_ENV = (
    "BUCKET",
    "ACCESS_KEY_ID",
    "SECRET_ACCESS_KEY",
    "ENDPOINT",
    "REGION",
    "MODEL_KEY",
)


class ModelLoadError(RuntimeError):
    """Error descriptivo al resolver, descargar o cargar el modelo."""


@lru_cache(maxsize=1)
def resolve_model_path() -> str:
    """Resuelve y valida el archivo del modelo según MODEL_STORAGE."""
    storage = os.getenv(MODEL_STORAGE_ENV, "local").strip().lower()

    if storage == "local":
        if not os.path.isfile(LOCAL_MODEL_PATH):
            raise FileNotFoundError(
                f"Modelo Keras local no encontrado. "
                f"Ruta esperada: {LOCAL_MODEL_PATH}"
            )
        return LOCAL_MODEL_PATH

    if storage == "railway":
        return _download_railway_model()

    raise ValueError(
        f"Valor inválido para {MODEL_STORAGE_ENV}: {storage!r}. "
        "Use 'local' o 'railway'."
    )


def _download_railway_model() -> str:
    values = {name: os.getenv(name, "").strip() for name in RAILWAY_REQUIRED_ENV}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ModelLoadError(
            "Faltan variables de entorno para cargar el modelo desde Railway: "
            + ", ".join(missing)
        )

    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=values["ENDPOINT"],
            region_name=values["REGION"],
            aws_access_key_id=values["ACCESS_KEY_ID"],
            aws_secret_access_key=values["SECRET_ACCESS_KEY"],
        )

        download_dir = tempfile.mkdtemp(prefix="artizan-model-")
        filename = os.path.basename(values["MODEL_KEY"])
        if not filename:
            raise ModelLoadError("MODEL_KEY debe incluir el nombre del archivo.")
        model_path = os.path.join(download_dir, filename)
        partial_path = f"{model_path}.part"

        client.download_file(values["BUCKET"], values["MODEL_KEY"], partial_path)
        if not os.path.isfile(partial_path) or os.path.getsize(partial_path) == 0:
            raise ModelLoadError(
                "La descarga del modelo terminó sin producir un archivo válido."
            )
        os.replace(partial_path, model_path)
        return model_path
    except Exception as exc:
        partial_path = locals().get("partial_path")
        if isinstance(partial_path, str):
            try:
                os.remove(partial_path)
            except FileNotFoundError:
                pass
        if isinstance(exc, ModelLoadError):
            raise
        raise ModelLoadError(
            "No se pudo descargar el modelo Keras desde Railway Bucket "
            f"(bucket={values['BUCKET']!r}, key={values['MODEL_KEY']!r})."
        ) from exc


_model: Any = None
_model_lock = threading.Lock()


def get_keras_model() -> Any:
    """Carga y reutiliza una única instancia del modelo Keras por proceso."""
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        from tensorflow import keras

        model_path = resolve_model_path()
        try:
            _model = keras.models.load_model(model_path)
        except Exception as exc:
            raise ModelLoadError(
                f"No se pudo cargar el modelo Keras desde: {model_path}"
            ) from exc
        return _model
