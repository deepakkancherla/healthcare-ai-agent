from pydantic import BaseModel

from app.application.service_interfaces import (
    ProviderDirectoryService,
    SchedulingWorkflowService,
)
from app.domain.models import ProviderSearchCriteria
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.tools.scheduling_context import (
    SYNTHETIC_CONVERSATION_ID,
    SYNTHETIC_MEMBER_ID,
)


class ProviderSearchRequest(BaseModel):
    location: str
    specialty: str
    gender: str | None = None


def provider_search(
    request: ProviderSearchRequest,
    service: ProviderDirectoryService | None = None,
    scheduling_workflows: SchedulingWorkflowService | None = None,
):
    """
    Adapt the model-facing request to the provider directory service.
    """
    provider_directory = (
        service or build_synthetic_services().provider_directory
    )
    criteria = ProviderSearchCriteria(
        location=request.location,
        specialty=request.specialty,
        gender=request.gender,
    )
    candidates = provider_directory.search(criteria)
    workflow_id = None
    workflow_state = None
    if scheduling_workflows is not None:
        workflow = scheduling_workflows.record_provider_search(
            member_id=SYNTHETIC_MEMBER_ID,
            conversation_id=SYNTHETIC_CONVERSATION_ID,
            criteria=criteria,
            candidates=candidates,
        )
        workflow_id = workflow.workflow_id
        workflow_state = workflow.state.value

    results = [
        {
            "provider_id": candidate.provider.provider_id,
            "provider_location_id": (
                candidate.location.provider_location_id
            ),
            "name": candidate.provider.display_name,
            "specialty": candidate.matched_specialty,
            "location": candidate.location.city,
            "address": candidate.location.address,
            "gender": candidate.provider.gender,
            "languages": list(candidate.provider.languages),
            "modalities": list(candidate.location.modalities),
        }
        for candidate in candidates
    ]
    if workflow_id is not None:
        for result in results:
            result["workflow_id"] = workflow_id
            result["workflow_state"] = workflow_state

    return results

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
