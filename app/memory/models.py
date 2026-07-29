from pydantic import BaseModel, Field


class UserMemory(BaseModel):
    user_id: str
    preferences: dict[str, str | list[str]] = Field(default_factory=dict)
