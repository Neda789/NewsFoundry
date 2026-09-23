import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.test import TestModel
from sqlmodel import Session, SQLModel

from database import engine, init_db
from main import app
from models import User
import routers.chat as chat_module


@pytest.fixture(autouse=True)
def fresh_db():
    """Réinitialise la base de test avant chaque test."""
    SQLModel.metadata.drop_all(engine)
    init_db()
    yield

@pytest.fixture(autouse=True)
def use_test_model():
    """Remplace le vrai LLM (Mistral) par un modèle factice pendant les tests."""
    with chat_module.agent.override(model=TestModel()):
        yield
@pytest.fixture(autouse=True)
def stub_top_news(monkeypatch):
    """Empêche les tests d'appeler la vraie WorldNewsAPI."""
    async def fake_get_top_news(*args, **kwargs):
        return [
            {"title": "Titre de test", "summary": "Résumé de test."},
        ]

    monkeypatch.setattr(chat_module, "get_top_news", fake_get_top_news)

@pytest.fixture
def client():
    return TestClient(app)


def _login(client, email="test@test.com", password="test") -> dict:
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_chats(client):
    headers = _login(client)

    r = client.get("/chats", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/chats", json={"title": "Ma discussion"}, headers=headers)
    assert r.status_code == 201
    assert "id" in r.json()

    r = client.get("/chats", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_send_message_gets_llm_response(client):
    headers = _login(client)

    r = client.post("/chats", json={}, headers=headers)
    chat_id = r.json()["id"]

    r = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Bonjour"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["role"] == "assistant"
    assert r.json()["content"]

    r = client.get(f"/chats/{chat_id}", headers=headers)
    assert r.status_code == 200
    messages = r.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_no_auth_rejected(client):
    r = client.get("/chats")
    assert r.status_code == 401

    r = client.post("/chats", json={})
    assert r.status_code == 401


def test_user_cannot_access_other_users_chat(client):
    headers = _login(client)
    r = client.post("/chats", json={}, headers=headers)
    chat_id = r.json()["id"]

    with Session(engine) as session:
        session.add(
            User(
                email="other@test.com",
                hashed_password=bcrypt.hashpw(b"other", bcrypt.gensalt()).decode(),
            )
        )
        session.commit()

    other_headers = _login(client, email="other@test.com", password="other")

    r = client.get(f"/chats/{chat_id}", headers=other_headers)
    assert r.status_code == 404

    r = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Coucou"},
        headers=other_headers,
    )
    assert r.status_code == 404