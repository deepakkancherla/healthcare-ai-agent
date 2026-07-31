from datetime import date

from pydantic import BaseModel

from app.application.service_interfaces import (
    MemberProfileService,
    NetworkVerificationService,
    ProviderDirectoryService,
    SchedulingWorkflowService,
)
from app.domain.models import NetworkStatus
from app.infrastructure.synthetic.fixtures.v1 import DEFAULT_SERVICE_DATE
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.tools.scheduling_context import (
    SYNTHETIC_CONVERSATION_ID,
    SYNTHETIC_MEMBER_ID,
)


class InsuranceVerificationRequest(BaseModel):
    insurance_name: str
    provider_name: str
    provider_location: str | None = None
    specialty: str | None = None
    service_date: date = DEFAULT_SERVICE_DATE
    policy_number: str | None = None
    subscriber_id: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None


class NetworkVerificationToolRequest(InsuranceVerificationRequest):
    provider_location: str
    specialty: str
    service_date: date


def verify_insurance(
    request: InsuranceVerificationRequest,
    member_profiles: MemberProfileService | None = None,
    provider_directory: ProviderDirectoryService | None = None,
    network_verification: NetworkVerificationService | None = None,
    scheduling_workflows: SchedulingWorkflowService | None = None,
):
    """
    Adapt the legacy insurance tool to plan-specific network verification.

    Member identity remains the Phase 0 hardcoded identity until the
    authentication boundary is introduced in Phase 4.
    """
    if (
        member_profiles is None
        or provider_directory is None
        or network_verification is None
    ):
        default_services = build_synthetic_services()
        member_profiles = (
            member_profiles or default_services.member_profiles
        )
        provider_directory = (
            provider_directory or default_services.provider_directory
        )
        network_verification = (
            network_verification
            or default_services.network_verification
        )

    coverage = member_profiles.get_member_context(
        member_id=SYNTHETIC_MEMBER_ID,
        service_date=request.service_date,
    )
    provider = provider_directory.resolve(
        provider_name=request.provider_name,
        provider_location=request.provider_location,
        specialty=request.specialty,
    )

    if provider is None:
        workflow_id, workflow_state = _record_network_failure(
            scheduling_workflows
        )
        return _response(
            request=request,
            status=NetworkStatus.UNKNOWN,
            reason="The provider or requested location was not found.",
            workflow_id=workflow_id,
            workflow_state=workflow_state,
        )

    plan_names = {
        coverage.health_plan.payer_id.casefold(),
        coverage.health_plan.product_name.casefold(),
    }
    if request.insurance_name.casefold() not in plan_names:
        workflow_id, workflow_state = _record_network_failure(
            scheduling_workflows
        )
        return _response(
            request=request,
            status=NetworkStatus.UNKNOWN,
            reason=(
                "The requested insurer does not match the member's "
                "active health plan."
            ),
            health_plan_id=coverage.health_plan.health_plan_id,
            network_id=coverage.network.network_id,
            provider_id=provider.provider.provider_id,
            provider_location_id=(
                provider.location.provider_location_id
            ),
            specialty=provider.matched_specialty,
            workflow_id=workflow_id,
            workflow_state=workflow_state,
        )

    result = network_verification.verify(
        coverage=coverage,
        provider_id=provider.provider.provider_id,
        provider_location_id=provider.location.provider_location_id,
        specialty_or_service_code=provider.matched_specialty,
        service_date=request.service_date,
    )
    workflow_id = None
    workflow_state = None
    if scheduling_workflows is not None:
        workflow = scheduling_workflows.start_or_resume(
            member_id=SYNTHETIC_MEMBER_ID,
            conversation_id=SYNTHETIC_CONVERSATION_ID,
        )
        workflow = scheduling_workflows.record_network_verification(
            workflow_id=workflow.workflow_id,
            result=result,
        )
        workflow_id = workflow.workflow_id
        workflow_state = workflow.state.value

    return _response(
        request=request,
        status=result.status,
        reason=result.reason,
        health_plan_id=result.health_plan_id,
        network_id=result.network_id,
        provider_id=result.provider_id,
        provider_location_id=result.provider_location_id,
        specialty=result.specialty_or_service_code,
        source_reference=result.source_reference,
        workflow_id=workflow_id,
        workflow_state=workflow_state,
    )


def _record_network_failure(
    scheduling_workflows: SchedulingWorkflowService | None,
) -> tuple[str | None, str | None]:
    if scheduling_workflows is None:
        return None, None

    workflow = scheduling_workflows.start_or_resume(
        member_id=SYNTHETIC_MEMBER_ID,
        conversation_id=SYNTHETIC_CONVERSATION_ID,
    )
    workflow = scheduling_workflows.record_network_failure(
        workflow.workflow_id
    )
    return workflow.workflow_id, workflow.state.value


def _response(
    request: InsuranceVerificationRequest,
    status: NetworkStatus,
    reason: str,
    health_plan_id: str | None = None,
    network_id: str | None = None,
    provider_id: str | None = None,
    provider_location_id: str | None = None,
    specialty: str | None = None,
    source_reference: str | None = None,
    workflow_id: str | None = None,
    workflow_state: str | None = None,
) -> dict:
    response = {
        "insurance_name": request.insurance_name,
        "provider_name": request.provider_name,
        "policy_number": request.policy_number or "N/A",
        "subscriber_id": request.subscriber_id or "N/A",
        "date_of_birth": request.date_of_birth or "N/A",
        "gender": request.gender or "N/A",
        "service_date": request.service_date.isoformat(),
        "network_status": status.value,
        "accepted": status == NetworkStatus.IN_NETWORK,
        "health_plan_id": health_plan_id,
        "network_id": network_id,
        "provider_id": provider_id,
        "provider_location_id": provider_location_id,
        "specialty": specialty,
        "source_reference": source_reference,
        "reason": reason,
    }
    if workflow_id is not None:
        response["workflow_id"] = workflow_id
        response["workflow_state"] = workflow_state
    return response


insurance_verification_tool = {
    "type": "function",
    "function": {
        "name": "verify_insurance",
        "description": (
            "Verify whether a provider participates in the member's "
            "active plan network for a location, specialty, and date."
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
                "provider_location": {
                    "type": "string",
                    "description": (
                        "City or address where the provider practices."
                    ),
                },
                "specialty": {
                    "type": "string",
                    "description": "Specialty or service being verified.",
                },
                "service_date": {
                    "type": "string",
                    "format": "date",
                    "description": (
                        "Date of service in YYYY-MM-DD format."
                    ),
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
            },
            "required": [
                "insurance_name",
                "provider_name",
                "provider_location",
                "specialty",
                "service_date",
            ],
        },
    },
}
