"""Tests for the NLP text generation endpoint."""

from unittest.mock import patch

_MOCK_OUTPUT = [{"generated_text": "Once upon a time there was a great adventure."}]


def test_generate_text(client, auth_headers):
    with patch("app.models.nlp.router.generate_text", return_value=_MOCK_OUTPUT):
        resp = client.post(
            "/models/nlp/generate",
            headers=auth_headers,
            json={"prompt": "Once upon a time"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt"] == "Once upon a time"
    assert len(data["results"]) == 1
    assert "generated_text" in data["results"][0]


def test_generate_text_empty_prompt(client, auth_headers):
    resp = client.post(
        "/models/nlp/generate",
        headers=auth_headers,
        json={"prompt": ""},
    )
    assert resp.status_code == 422


def test_generate_text_exceeds_max_tokens(client, auth_headers):
    resp = client.post(
        "/models/nlp/generate",
        headers=auth_headers,
        json={"prompt": "Hello world", "max_new_tokens": 201},
    )
    assert resp.status_code == 422


def test_generate_text_requires_auth(client):
    resp = client.post(
        "/models/nlp/generate",
        json={"prompt": "Hello"},
    )
    assert resp.status_code == 401


def test_generate_multiple_sequences(client, auth_headers):
    mock_outputs = [
        {"generated_text": "Hello world is a great place."},
        {"generated_text": "Hello world is where dreams come true."},
    ]
    with patch("app.models.nlp.router.generate_text", return_value=mock_outputs):
        resp = client.post(
            "/models/nlp/generate",
            headers=auth_headers,
            json={"prompt": "Hello world", "num_return_sequences": 2},
        )
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2
