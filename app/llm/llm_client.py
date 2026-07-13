# app/llm/client.py

from openai import OpenAI

from app.config import OPENAI_API_KEY


def get_llm_client():
    """
    Creates and returns an OpenAI client.
    """

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=OPENAI_API_KEY)