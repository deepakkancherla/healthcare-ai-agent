import pytest
from pydantic import ValidationError

from app.domain.models import ProviderSearchCriteria
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.infrastructure.synthetic.fixtures.v1 import (
    DEFAULT_SERVICE_DATE,
)
from app.tools.availability import (
    AppointmentSelectionRequest,
    AvailabilitySearchRequest,
    appointment_selection_tool,
    availability_search_tool,
    search_availability,
    select_appointment_slot,
)


@pytest.fixture
def services():
    return build_synthetic_services()


def _prepare_verified_workflow(services):
    criteria = ProviderSearchCriteria(
        location="Plano",
        specialty="Dermatology",
        gender="Female",
    )
    candidates = services.provider_directory.search(criteria)
    workflow = services.scheduling_workflows.record_provider_search(
        "deepak",
        "conversation-deepak",
        criteria,
        candidates,
    )
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    candidate = candidates[0]
    result = services.network_verification.verify(
        coverage=coverage,
        provider_id=candidate.provider.provider_id,
        provider_location_id=(
            candidate.location.provider_location_id
        ),
        specialty_or_service_code=candidate.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )
    services.scheduling_workflows.record_network_verification(
        workflow.workflow_id,
        result,
    )


def test_availability_tool_returns_authoritative_slots(services):
    _prepare_verified_workflow(services)

    result = search_availability(
        AvailabilitySearchRequest(
            provider_id="provider-sarah-johnson",
            provider_location_id="location-sarah-plano",
            start_date="2026-08-04",
            end_date="2026-08-04",
            modality="in_person",
        ),
        services.availability,
        services.scheduling_workflows,
    )

    assert result["workflow_state"] == "awaiting_selection"
    assert [slot["slot_id"] for slot in result["slots"]] == [
        "slot-sarah-plano-20260804-1000"
    ]
    assert result["slots"][0]["version"] == 1


def test_selection_tool_stops_at_awaiting_confirmation(services):
    _prepare_verified_workflow(services)
    search_availability(
        AvailabilitySearchRequest(
            provider_id="provider-sarah-johnson",
            provider_location_id="location-sarah-plano",
            start_date="2026-08-04",
            end_date="2026-08-04",
        ),
        services.availability,
        services.scheduling_workflows,
    )

    result = select_appointment_slot(
        AppointmentSelectionRequest(
            slot_id="slot-sarah-plano-20260804-1000"
        ),
        services.availability,
        services.scheduling_workflows,
    )

    assert result["workflow_state"] == "awaiting_confirmation"
    assert result["requires_confirmation"] is True
    assert result["selection"]["network_status"] == "in_network"
    assert result["selection"]["network_id"] == (
        "network-bcbs-choice"
    )
    assert "confirmation_number" not in result


def test_availability_tool_validates_date_range():
    with pytest.raises(ValidationError, match="start date"):
        AvailabilitySearchRequest(
            provider_id="provider-sarah-johnson",
            provider_location_id="location-sarah-plano",
            start_date="2026-08-05",
            end_date="2026-08-04",
        )


@pytest.mark.parametrize(
    "definition",
    [
        availability_search_tool,
        appointment_selection_tool,
    ],
)
def test_scheduling_tools_do_not_accept_authoritative_member_fields(
    definition,
):
    properties = definition["function"]["parameters"]["properties"]

    assert "member_id" not in properties
    assert "network_status" not in properties
