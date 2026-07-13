from pydantic import BaseModel


class InsuranceVerificationRequest(BaseModel):
    insurance_name: str
    provider_name: str
    policy_number: str | None = None
    subscriber_id: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None


def verify_insurance(request: InsuranceVerificationRequest):
    """
    Verify insurance coverage.

    (Hardcoded implementation for now.)
    """

    return {
        "insurance_name": "BCBS",
        "provider_name": request.provider_name,
        "policy_number": request.policy_number or "N/A",
        "subscriber_id": request.subscriber_id or "N/A",
        "date_of_birth": request.date_of_birth or "N/A",
        "gender": request.gender or "N/A",
        "accepted": True,
    }


insurance_verification_tool = {
    "type": "function",
    "function": {
        "name": "verify_insurance",
        "description": (
            "Verify insurance coverage based on "
            "insurance name, provider name, and optional details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "insurance_name": {
                    "type": "string",
                    "description": "Name of the insurance company.",
                },
                "provider_name": {
                    "type": "string",
                    "description": "Name of the healthcare provider.",
                },
                "policy_number": {
                    "type": "string",
                    "description": "Policy number (optional).",
                },
                "subscriber_id": {
                    "type": "string",
                    "description": "Subscriber ID (optional).",
                },
                "date_of_birth": {
                    "type": "string",
                    "description": ("Date of birth in YYYY-MM-DD format (optional)."),
                },
                "gender": {"type": "string", "description": "Gender (optional)."},
                "accepted": {
                    "type": "boolean",
                    "description": "Whether the insurance is accepted.",
                },
            },
            "required": ["insurance_name", "provider_name"],
        },
    },
}
