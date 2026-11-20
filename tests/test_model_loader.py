"""Tests for local and Railway Bucket Keras model loading."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app import model_loader


@pytest.fixture(autouse=True)
def reset_model_loader_cache():
    model_loader.resolve_model_path.cache_clear()
    model_loader._model = None
    yield
    model_loader.resolve_model_path.cache_clear()
    model_loader._model = None


def test_resolves_local_model_without_bucket_credentials(tmp_path, monkeypatch):
    model_path = tmp_path / "modelo_pinturas_gridsearch.keras"
    model_path.write_bytes(b"model")
    monkeypatch.setattr(model_loader, "LOCAL_MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_STORAGE", "local")

    assert model_loader.resolve_model_path() == str(model_path)


def test_missing_local_model_reports_expected_path(tmp_path, monkeypatch):
    model_path = tmp_path / "missing.keras"
    monkeypatch.setattr(model_loader, "LOCAL_MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_STORAGE", "local")

    with pytest.raises(FileNotFoundError, match=r"missing\.keras"):
        model_loader.resolve_model_path()


def _set_railway_environment(monkeypatch):
    monkeypatch.setenv("MODEL_STORAGE", "railway")
    monkeypatch.setenv("BUCKET", "art-models")
    monkeypatch.setenv("ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("ENDPOINT", "https://bucket.example.invalid")
    monkeypatch.setenv("REGION", "auto")
    monkeypatch.setenv("MODEL_KEY", "models/modelo_pinturas_gridsearch.keras")


def test_railway_model_is_downloaded_atomically_once(tmp_path, monkeypatch):
    _set_railway_environment(monkeypatch)
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    monkeypatch.setattr(
        model_loader.tempfile, "mkdtemp", lambda prefix: str(download_dir)
    )
    client = Mock()

    def download_file(bucket, key, filename):
        assert bucket == "art-models"
        assert key == "models/modelo_pinturas_gridsearch.keras"
        Path(filename).write_bytes(b"complete-model")

    client.download_file.side_effect = download_file
    with patch("boto3.client", return_value=client) as client_factory:
        first_path = model_loader.resolve_model_path()
        second_path = model_loader.resolve_model_path()

    assert first_path == second_path
    assert Path(first_path).read_bytes() == b"complete-model"
    assert not Path(f"{first_path}.part").exists()
    client_factory.assert_called_once()
    client.download_file.assert_called_once()


def test_failed_railway_download_does_not_leave_partial_file(
    tmp_path, monkeypatch
):
    _set_railway_environment(monkeypatch)
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    monkeypatch.setattr(
        model_loader.tempfile, "mkdtemp", lambda prefix: str(download_dir)
    )
    client = Mock()

    def download_file(bucket, key, filename):
        Path(filename).write_bytes(b"incomplete")
        raise OSError("connection interrupted")

    client.download_file.side_effect = download_file
    with patch("boto3.client", return_value=client):
        with pytest.raises(
            model_loader.ModelLoadError, match="No se pudo descargar"
        ) as exc_info:
            model_loader.resolve_model_path()

    assert isinstance(exc_info.value.__cause__, OSError)
    assert not list(download_dir.iterdir())


def test_railway_configuration_requires_all_variables(monkeypatch):
    monkeypatch.setenv("MODEL_STORAGE", "railway")

    with pytest.raises(model_loader.ModelLoadError) as exc_info:
        model_loader.resolve_model_path()

    message = str(exc_info.value)
    for variable in model_loader.RAILWAY_REQUIRED_ENV:
        assert variable in message
    assert "test-secret-key" not in message


def test_keras_model_is_reused_after_first_load(tmp_path, monkeypatch):
    model_path = tmp_path / "model.keras"
    model_path.write_bytes(b"model")
    monkeypatch.setattr(model_loader, "LOCAL_MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_STORAGE", "local")
    loaded_model = Mock()

    with patch(
        "tensorflow.keras.models.load_model", return_value=loaded_model
    ) as load_model:
        assert model_loader.get_keras_model() is loaded_model
        assert model_loader.get_keras_model() is loaded_model

    load_model.assert_called_once_with(str(model_path))
