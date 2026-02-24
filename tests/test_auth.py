"""Tests for the auth module."""

import pytest


def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={"username": "newuser", "email": "new@example.com", "password": "Pass1234!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "hashed_password" not in data


def test_register_duplicate_username(client, registered_user):
    resp = client.post(
        "/auth/register",
        json={
            "username": registered_user["username"],
            "email": "other@example.com",
            "password": "Pass1234!",
        },
    )
    assert resp.status_code == 400
    assert "Username already registered" in resp.json()["detail"]


def test_register_duplicate_email(client, registered_user):
    resp = client.post(
        "/auth/register",
        json={
            "username": "otherusername",
            "email": registered_user["email"],
            "password": "Pass1234!",
        },
    )
    assert resp.status_code == 400
    assert "Email already registered" in resp.json()["detail"]


def test_login_success(client, registered_user):
    resp = client.post(
        "/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, registered_user):
    resp = client.post(
        "/auth/login",
        data={"username": registered_user["username"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_get_current_user(client, auth_headers, registered_user):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == registered_user["username"]


def test_get_current_user_unauthenticated(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
