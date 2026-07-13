from pydantic import BaseModel


class ProviderSearchRequest(BaseModel):
    location: str
    specialty: str
    gender: str | None = None


def provider_search(request: ProviderSearchRequest):
    """
    Search providers.

    (Hardcoded implementation for now.)
    """

    return [
        {
            "name": "Dr. Sarah Johnson",
            "specialty": request.specialty,
            "location": request.location,
            "gender": "Female",
        }
    ]

provider_search_tool = {
    "type": "function",
    "function": {
        "name": "provider_search",
        "description": (
            "Search for healthcare providers based on "
            "location, specialty, and optional gender."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or location."
                },
                "specialty": {
                    "type": "string",
                    "description": "Medical specialty."
                },
                "gender": {
                    "type": "string",
                    "description": "Preferred provider gender."
                }
            },
            "required": [
                "location",
                "specialty"
            ]
        }
    }
}