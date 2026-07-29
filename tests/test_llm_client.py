from unittest.mock import Mock

import pytest

from app.llm import llm_client


def test_get_llm_client_requires_an_api_key(monkeypatch):
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not configured"):
        llm_client.get_llm_client()


def test_get_llm_client_constructs_client_without_network_access(monkeypatch):
    expected_client = object()
    openai_factory = Mock(return_value=expected_client)
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", "test-api-key")
    monkeypatch.setattr(llm_client, "OpenAI", openai_factory)

    client = llm_client.get_llm_client()

    assert client is expected_client
    openai_factory.assert_called_once_with(api_key="test-api-key")
