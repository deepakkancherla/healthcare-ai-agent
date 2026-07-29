import logging

from app.agent.healthcare_agent import HealthcareAgent
from app.config import configure_logging
from app.memory.memory_manager import MemoryManager
from app.tools.tool_registry import ToolRegistry

memory_manager_tool = MemoryManager()
memory_manager_tool.save("deepak", "insurance", "BCBS")
memory_manager_tool.save("deepak", "preferred_city", "Plano")
tool_registry = ToolRegistry()

configure_logging()
logger = logging.getLogger(__name__)

agent = HealthcareAgent(
    tool_registry=tool_registry, memory_manager=memory_manager_tool
)  # Replace with actual instances if needed

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    logger.info("Received CLI chat request.")
    response = agent.chat(user_input)

    logger.info("Assistant: %s", response)
