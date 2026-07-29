from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes.chat import get_healthcare_agent


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def override_agent(agent):
    app.dependency_overrides[get_healthcare_agent] = lambda: agent


def test_chat_route_delegates_to_agent(client):
    agent = Mock()
    agent.chat.return_value = "How can I help?"
    override_agent(agent)

    response = client.post(
        "/chat",
        json={"message": "  Hello  "},
    )

    assert response.status_code == 200
    assert response.json() == {"response": "How can I help?"}
    agent.chat.assert_called_once_with("Hello")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "   "},
    ],
)
def test_chat_route_rejects_invalid_requests(client, payload):
    agent = Mock()
    override_agent(agent)

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    agent.chat.assert_not_called()


def test_chat_route_returns_500_when_agent_fails(client):
    agent = Mock()
    agent.chat.side_effect = RuntimeError("model unavailable")
    override_agent(agent)

    response = client.post(
        "/chat",
        json={"message": "Hello"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to process the request at this time."
    }


def test_service_status_route(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Healthcare AI Agent",
        "status": "running",
        "version": "1.0.0",
    }
