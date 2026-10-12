import logging

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import register_error_handlers
from app.middleware import LoggingMiddleware


class NumericPayload(BaseModel):
    value: int


def test_unhandled_exception_returns_safe_error_and_is_logged(caplog):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)
    register_error_handlers(app)

    @app.get("/unexpected-error")
    def raise_unexpected_error():
        raise RuntimeError("private /internal/database failure")

    with caplog.at_level(logging.ERROR, logger="artizan.requests"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
    assert "private /internal/database failure" not in response.text
    assert "private /internal/database failure" in caplog.text


def test_validation_and_http_errors_use_consistent_detail():
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/validation")
    def validate_payload(payload: NumericPayload):
        return payload

    @app.get("/unauthorized")
    def raise_unauthorized():
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/internal-http-error")
    def raise_internal_http_error():
        raise HTTPException(status_code=500, detail="private SQL /internal/database failure")

    with TestClient(app) as client:
        invalid_response = client.post("/validation", json={"value": "sensitive-input"})
        unauthorized_response = client.get("/unauthorized")
        internal_response = client.get("/internal-http-error")

    assert invalid_response.status_code == 422
    assert invalid_response.json() == {"detail": "Invalid request data."}
    assert "sensitive-input" not in invalid_response.text
    assert unauthorized_response.status_code == 401
    assert unauthorized_response.json() == {"detail": "Could not validate credentials"}
    assert unauthorized_response.headers["www-authenticate"] == "Bearer"
    assert internal_response.status_code == 500
    assert internal_response.json() == {"detail": "An unexpected error occurred."}
    assert "private SQL /internal/database failure" not in internal_response.text