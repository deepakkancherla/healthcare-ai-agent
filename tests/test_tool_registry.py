import pytest
from pydantic import BaseModel, ValidationError

from app.tools.tool_registry import RegisteredTool, ToolRegistry


class ExampleToolRequest(BaseModel):
    value: int


def example_handler(request: ExampleToolRequest) -> dict:
    return {"doubled": request.value * 2}


def example_tool_definition() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "example",
            "description": "Double a value.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
        },
    }


def test_tool_registry_registers_definition_and_executes_handler():
    registry = ToolRegistry()
    definition = example_tool_definition()
    registry.register(
        "example",
        RegisteredTool(
            definition=definition,
            request_model=ExampleToolRequest,
            handler=example_handler,
        ),
    )

    assert registry.get_tool_definitions() == [definition]
    assert registry.execute("example", {"value": 4}) == {"doubled": 8}


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"value": "not-an-integer"},
    ],
)
def test_tool_registry_validates_arguments(arguments):
    registry = ToolRegistry()
    registry.register(
        "example",
        RegisteredTool(
            definition=example_tool_definition(),
            request_model=ExampleToolRequest,
            handler=example_handler,
        ),
    )

    with pytest.raises(ValidationError):
        registry.execute("example", arguments)


def test_tool_registry_propagates_handler_errors():
    registry = ToolRegistry()

    def failing_handler(_: ExampleToolRequest):
        raise RuntimeError("tool failed")

    registry.register(
        "example",
        RegisteredTool(
            definition=example_tool_definition(),
            request_model=ExampleToolRequest,
            handler=failing_handler,
        ),
    )

    with pytest.raises(RuntimeError, match="tool failed"):
        registry.execute("example", {"value": 1})
