import logging

from app.agent.healthcare_agent import HealthcareAgent
from app.config import configure_logging


configure_logging()
logger = logging.getLogger(__name__)

agent = HealthcareAgent()

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    logger.info("Received CLI chat request.")
    response = agent.chat(user_input)

    logger.info("Assistant: %s", response)
