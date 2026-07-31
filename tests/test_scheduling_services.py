from datetime import date, datetime, timezone

import pytest

from app.application.scheduling_services import (
    InvalidWorkflowTransition,
    SlotNotFoundError,
)
from app.domain.models import (
    AvailabilityQuery,
    NetworkStatus,
    ProviderSearchCriteria,
    WorkflowState,
)
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.infrastructure.synthetic.fixtures.v1 import (
    DEFAULT_SERVICE_DATE,
)


@pytest.fixture
def services():
    return build_synthetic_services()


def _advance_to_searching_availability(services):
    criteria = ProviderSearchCriteria(
        location="Plano",
        specialty="Dermatology",
        gender="Female",
    )
    candidates = services.provider_directory.search(criteria)
    workflow = services.scheduling_workflows.record_provider_search(
        member_id="deepak",
        conversation_id="conversation-deepak",
        criteria=criteria,
        candidates=candidates,
    )
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    candidate = candidates[0]
    network_result = services.network_verification.verify(
        coverage=coverage,
        provider_id=candidate.provider.provider_id,
        provider_location_id=(
            candidate.location.provider_location_id
        ),
        specialty_or_service_code=candidate.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )
    workflow = (
        services.scheduling_workflows.record_network_verification(
            workflow.workflow_id,
            network_result,
        )
    )
    return workflow


def _availability_query(
    start_date: date = date(2026, 8, 4),
    end_date: date = date(2026, 8, 5),
    modality: str | None = None,
) -> AvailabilityQuery:
    return AvailabilityQuery(
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        start_date=start_date,
        end_date=end_date,
        modality=modality,
    )


def test_availability_search_filters_date_modality_and_status(
    services,
):
    slots = services.availability.search(
        _availability_query(modality="in_person")
    )

    assert [slot.slot_id for slot in slots] == [
        "slot-sarah-plano-20260804-1000"
    ]
    assert all(slot.status == "available" for slot in slots)


def test_availability_search_returns_no_slots_for_empty_range(
    services,
):
    slots = services.availability.search(
        _availability_query(
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 11),
        )
    )

    assert slots == []


def test_availability_query_rejects_reversed_date_range():
    with pytest.raises(ValueError, match="start date"):
        _availability_query(
            start_date=date(2026, 8, 5),
            end_date=date(2026, 8, 4),
        )


def test_get_current_slot_rejects_unknown_identifier(services):
    with pytest.raises(SlotNotFoundError, match="missing-slot"):
        services.availability.get_current_slot("missing-slot")


def test_workflow_valid_transitions_reach_awaiting_confirmation(
    services,
):
    workflow = _advance_to_searching_availability(services)
    assert workflow.state == WorkflowState.SEARCHING_AVAILABILITY

    query = _availability_query(modality="in_person")
    slots = services.availability.search(query)
    workflow = services.scheduling_workflows.record_availability(
        workflow.workflow_id,
        query,
        slots,
    )
    assert workflow.state == WorkflowState.AWAITING_SELECTION

    workflow = services.scheduling_workflows.select_slot(
        workflow.workflow_id,
        slots[0],
    )

    assert workflow.state == WorkflowState.AWAITING_CONFIRMATION
    assert workflow.selection is not None
    assert workflow.selection.slot_id == (
        "slot-sarah-plano-20260804-1000"
    )
    assert workflow.selection.slot_version == 1
    assert workflow.selection.network_status == (
        NetworkStatus.IN_NETWORK
    )
    assert workflow.selection.network_id == "network-bcbs-choice"
    assert workflow.selection.network_source_reference == (
        "synthetic:v1:bcbs-sarah-plano"
    )
    assert workflow.version == 7


def test_workflow_rejects_selection_before_options_are_presented(
    services,
):
    workflow = services.scheduling_workflows.start_or_resume(
        "deepak",
        "conversation-deepak",
    )
    slot = services.availability.get_current_slot(
        "slot-sarah-plano-20260804-1000"
    )

    with pytest.raises(
        InvalidWorkflowTransition,
        match="not presented",
    ):
        services.scheduling_workflows.select_slot(
            workflow.workflow_id,
            slot,
        )


def test_workflow_rejects_invalid_state_transition(services):
    workflow = services.scheduling_workflows.start_or_resume(
        "deepak",
        "conversation-deepak",
    )

    with pytest.raises(
        InvalidWorkflowTransition,
        match=(
            "collecting_requirements to collecting_requirements"
        ),
    ):
        services.scheduling_workflows.record_network_failure(
            workflow.workflow_id
        )


def test_workflow_rejects_network_result_for_non_candidate(
    services,
):
    criteria = ProviderSearchCriteria(
        location="Plano",
        specialty="Dermatology",
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
    wrong_provider_result = services.network_verification.verify(
        coverage=coverage,
        provider_id="provider-miguel-rivera",
        provider_location_id="location-miguel-plano",
        specialty_or_service_code="Cardiology",
        service_date=DEFAULT_SERVICE_DATE,
    )

    with pytest.raises(
        InvalidWorkflowTransition,
        match="provider candidate",
    ):
        services.scheduling_workflows.record_network_verification(
            workflow.workflow_id,
            wrong_provider_result,
        )


def test_no_availability_returns_to_requirement_collection(
    services,
):
    workflow = _advance_to_searching_availability(services)
    query = _availability_query(
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 11),
    )

    workflow = services.scheduling_workflows.record_availability(
        workflow.workflow_id,
        query,
        [],
    )

    assert workflow.state == WorkflowState.COLLECTING_REQUIREMENTS
    assert workflow.available_slot_ids == ()


def test_workflow_is_persisted_separately_by_conversation(services):
    created = services.scheduling_workflows.start_or_resume(
        "deepak",
        "conversation-deepak",
    )
    loaded = services.scheduling_workflows.get_for_conversation(
        "deepak",
        "conversation-deepak",
    )

    assert loaded == created
    assert created.created_at.tzinfo is not None
    assert created.created_at <= datetime.now(timezone.utc)
