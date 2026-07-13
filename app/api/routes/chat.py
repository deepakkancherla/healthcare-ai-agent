import logging
from functools import lru_cache
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.healthcare_agent import HealthcareAgent
from app.api.schemas import ChatRequest, ChatResponse


logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

agent_lock = Lock()


@lru_cache(maxsize=1)
def get_healthcare_agent() -> HealthcareAgent:
    try:
        return HealthcareAgent()
    except Exception as error:
        logger.exception("Failed to initialize the healthcare agent.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The healthcare service is temporarily unavailable.",
        ) from error


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "The healthcare agent could not process the request."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The healthcare agent is temporarily unavailable."
        },
    },
)
def chat(
    request: ChatRequest,
    agent: Annotated[HealthcareAgent, Depends(get_healthcare_agent)],
) -> ChatResponse:
    logger.info("Received chat request.")

    try:
        with agent_lock:
            response = agent.chat(request.message)
    except Exception as error:
        logger.exception("Healthcare agent failed to process a chat request.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process the request at this time.",
        ) from error

    logger.info("Chat request completed successfully.")

    return ChatResponse(response=response)
