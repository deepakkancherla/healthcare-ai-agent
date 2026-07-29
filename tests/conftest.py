from collections.abc import Callable, Iterable
from types import SimpleNamespace

import pytest

from app.agent.healthcare_agent import HealthcareAgent
from app.memory.memory_manager import MemoryManager
from app.tools.tool_registry import ToolRegistry


def assistant_message(
    content: str | None = None,
    tool_calls: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
    )


def tool_call(
    tool_call_id: str,
    name: str,
    arguments: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=tool_call_id,
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        ),
    )


class FakeCompletions:
    def __init__(
        self,
        responses: Iterable[
            SimpleNamespace
            | Exception
            | Callable[[dict], SimpleNamespace]
        ],
    ):
        self.responses = iter(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        response = next(self.responses)

        if isinstance(response, Exception):
            raise response

        if callable(response):
            response = response(kwargs)

        return SimpleNamespace(
            choices=[SimpleNamespace(message=response)],
        )


class FakeOpenAIClient:
    def __init__(
        self,
        responses: Iterable[
            SimpleNamespace
            | Exception
            | Callable[[dict], SimpleNamespace]
        ],
    ):
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


@pytest.fixture
def agent_factory(monkeypatch):
    def create_agent(
        responses,
        *,
        memory_manager: MemoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> tuple[HealthcareAgent, FakeOpenAIClient]:
        client = FakeOpenAIClient(responses)
        monkeypatch.setattr(
            "app.agent.healthcare_agent.get_llm_client",
            lambda: client,
        )

        agent = HealthcareAgent(
            tool_registry=tool_registry or ToolRegistry(),
            memory_manager=memory_manager or MemoryManager(),
        )

        return agent, client

    return create_agent
