import logging
import sys
from pathlib import Path

import requests
import streamlit as st

# Streamlit adds the script's directory (app/ui) to sys.path when this file is
# launched directly. Add the repository root so the app package can be imported
# by the documented command: streamlit run app/ui/streamlit_app.py.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import configure_logging, get_backend_url


REQUEST_TIMEOUT_SECONDS = 120

configure_logging()
logger = logging.getLogger(__name__)

chat_url = f"{get_backend_url()}/chat"


def request_assistant_response(message: str) -> tuple[str, bool]:
    try:
        response = requests.post(
            chat_url,
            json={"message": message},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        response_data = response.json()

        if not isinstance(response_data, dict):
            raise ValueError("The backend returned an invalid response.")

        assistant_response = response_data.get("response")

        if not isinstance(assistant_response, str) or not assistant_response.strip():
            raise ValueError("The backend returned an invalid response.")

        return assistant_response.strip(), False
    except requests.Timeout:
        logger.error("Healthcare API request timed out.")
        return (
            "The healthcare service is taking longer than expected. "
            "Please try again.",
            True,
        )
    except requests.ConnectionError:
        logger.error("Unable to connect to the healthcare API.")
        return (
            "I couldn't connect to the healthcare service. "
            "Please make sure the backend is running and try again.",
            True,
        )
    except requests.HTTPError as error:
        logger.error(
            "Healthcare API returned HTTP status %s.",
            error.response.status_code if error.response is not None else "unknown",
        )
        return (
            "The healthcare service couldn't process your request. "
            "Please try again in a moment.",
            True,
        )
    except (requests.RequestException, ValueError):
        logger.exception("Healthcare API returned an unexpected response.")
        return (
            "I received an unexpected response from the healthcare service. "
            "Please try again.",
            True,
        )


st.set_page_config(
    page_title="Healthcare AI Assistant",
    page_icon="🏥",
)

st.title("Healthcare AI Assistant")
st.caption("AI-powered healthcare scheduling assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["is_error"]:
            st.error(message["content"])
        else:
            st.markdown(message["content"])

if user_message := st.chat_input("How can I help with your healthcare needs?"):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
            "is_error": False,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Working on your request..."):
            assistant_response, is_error = request_assistant_response(user_message)

        if is_error:
            st.error(assistant_response)
        else:
            st.markdown(assistant_response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_response,
            "is_error": is_error,
        }
    )
