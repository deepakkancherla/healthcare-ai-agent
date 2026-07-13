from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel


@dataclass
class RegisteredTool:
    """
    Represents a tool that can be executed by the agent.
    """

    definition: dict
    request_model: type[BaseModel]
    handler: Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, name: str, tool: RegisteredTool):
        self._tools[name] = tool

    def get_tool_definitions(self):

        return [tool.definition for tool in self._tools.values()]

    def execute(self, tool_name: str, arguments: dict):

        tool = self._tools[tool_name]

        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        request = tool.request_model.model_validate(arguments)

        return tool.handler(request)
