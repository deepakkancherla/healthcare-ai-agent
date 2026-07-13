from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def validate_message(cls, message: str) -> str:
        message = message.strip()

        if not message:
            raise ValueError("Message must not be empty.")

        return message


class ChatResponse(BaseModel):
    response: str


class ServiceStatusResponse(BaseModel):
    service: str
    status: str
    version: str
