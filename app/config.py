import logging
import os

from dotenv import load_dotenv


load_dotenv()

APP_NAME = "Healthcare AI Agent"
APP_VERSION = "1.0.0"
DEFAULT_BACKEND_URL = "http://localhost:8000"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

DEFAULT_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2


def get_backend_url() -> str:
    return (
        os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip().rstrip("/")
        or DEFAULT_BACKEND_URL
    )


def configure_logging() -> None:
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger().setLevel(log_level)
