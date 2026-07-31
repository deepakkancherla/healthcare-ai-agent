from dataclasses import replace
from datetime import timedelta

import pytest

from app.application.booking_errors import (
    BookingOutcomeUnknown,
    ConfirmationExpired,
    ConfirmationFingerprintMismatch,
    ConfirmationNotPrepared,
    ExplicitConfirmationRequired,
    InvalidBookingState,
    SlotReservationConflict,
)
from app.application.booking_services import (
    DefaultAppointmentBookingService,
)
from app.domain.models import ExplicitConfirmation, WorkflowState

from .booking_helpers import (
    MutableClock,
    build_selected_booking_context,
)


def _confirm(confirmed: bool = True) -> ExplicitConfirmation:
    return ExplicitConfirmation(confirmed=confirmed)


def test_confirmation_summary_contains_exact_selected_details():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )

    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    assert confirmation.summary.provider_name == "Dr. Sarah Johnson"
    assert confirmation.summary.specialty == "Dermatology"
    assert confirmation.summary.location == (
        "100 Synthetic Health Way, Plano, TX 75024"
    )
    assert confirmation.summary.start_at.isoformat() == (
        "2026-08-04T10:00:00-05:00"
    )
    assert confirmation.summary.time_zone == "America/Chicago"
    assert confirmation.summary.modality == "in_person"
    assert confirmation.summary.network_status.value == "in_network"
    assert confirmation.summary.limitations
    assert len(confirmation.selection_fingerprint) == 64
    assert repositories.appointments.list_all() == []


def test_confirmation_fingerprint_is_stable_for_same_selection():
    _, services, workflow, clock = build_selected_booking_context()

    first = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )
    clock.advance(timedelta(minutes=1))
    second = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    assert first.selection_fingerprint == second.selection_fingerprint
    assert first.presented_at != second.presented_at


def test_confirmation_fingerprint_changes_with_selection():
    _, first_services, first_workflow, _ = (
        build_selected_booking_context()
    )
    _, second_services, second_workflow, _ = (
        build_selected_booking_context(
            slot_id="slot-sarah-plano-20260805-1400"
        )
    )

    first = first_services.appointment_booking.prepare_confirmation(
        first_workflow.workflow_id
    )
    second = (
        second_services.appointment_booking.prepare_confirmation(
            second_workflow.workflow_id
        )
    )

    assert first.selection_fingerprint != second.selection_fingerprint


def test_booking_requires_explicit_confirmation():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )
    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    with pytest.raises(ExplicitConfirmationRequired):
        services.appointment_booking.book(
            workflow.workflow_id,
            confirmation.selection_fingerprint,
            _confirm(False),
        )

    assert repositories.appointments.list_all() == []
    assert services.scheduling_workflows.get(
        workflow.workflow_id
    ).state == WorkflowState.AWAITING_CONFIRMATION


def test_booking_rejects_invalid_workflow_state():
    _, services, _, _ = build_selected_booking_context()
    workflow = services.scheduling_workflows.start_or_resume(
        "deepak",
        "different-conversation",
    )

    with pytest.raises(InvalidBookingState):
        services.appointment_booking.book(
            workflow.workflow_id,
            "0" * 64,
            _confirm(),
        )


def test_booking_rejects_missing_prepared_confirmation():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )

    with pytest.raises(ConfirmationNotPrepared):
        services.appointment_booking.book(
            workflow.workflow_id,
            "0" * 64,
            _confirm(),
        )

    assert repositories.appointments.list_all() == []


def test_booking_rejects_mismatched_fingerprint():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )
    services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    with pytest.raises(ConfirmationFingerprintMismatch):
        services.appointment_booking.book(
            workflow.workflow_id,
            "0" * 64,
            _confirm(),
        )

    assert repositories.appointments.list_all() == []


def test_expired_confirmation_is_invalidated():
    clock = MutableClock()
    repositories, services, workflow, _ = (
        build_selected_booking_context(
            clock=clock,
            confirmation_ttl=timedelta(minutes=5),
        )
    )
    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )
    clock.advance(timedelta(minutes=6))

    with pytest.raises(ConfirmationExpired):
        services.appointment_booking.book(
            workflow.workflow_id,
            confirmation.selection_fingerprint,
            _confirm(),
        )

    current = services.scheduling_workflows.get(workflow.workflow_id)
    assert current.state == WorkflowState.AWAITING_SELECTION
    assert current.selection is None
    assert current.confirmation is None
    assert repositories.appointments.list_all() == []


@pytest.mark.parametrize("new_status", ["available", "booked"])
def test_changed_or_unavailable_slot_is_not_booked(new_status):
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )
    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )
    slot = repositories.slots.get(
        "slot-sarah-plano-20260804-1000"
    )
    assert slot is not None
    repositories.slots.update(
        replace(
            slot,
            status=new_status,
            version=slot.version + 1,
        ),
        expected_version=slot.version,
    )

    with pytest.raises(SlotReservationConflict):
        services.appointment_booking.book(
            workflow.workflow_id,
            confirmation.selection_fingerprint,
            _confirm(),
        )

    current = services.scheduling_workflows.get(workflow.workflow_id)
    assert current.state == WorkflowState.SEARCHING_AVAILABILITY
    assert current.confirmation is None
    assert repositories.appointments.list_all() == []


def test_successful_booking_returns_repository_confirmation():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )
    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    appointment = services.appointment_booking.book(
        workflow.workflow_id,
        confirmation.selection_fingerprint,
        _confirm(),
    )

    assert repositories.appointments.get(
        appointment.appointment_id
    ) == appointment
    assert appointment.status == "confirmed"
    assert appointment.confirmation_number.startswith("SYN-")
    assert services.scheduling_workflows.get(
        workflow.workflow_id
    ).state == WorkflowState.CONFIRMED
    slot = repositories.slots.get(appointment.slot_id)
    assert slot is not None
    assert slot.status == "booked"
    assert slot.version == 2


def test_repeated_confirmation_returns_one_appointment():
    repositories, services, workflow, _ = (
        build_selected_booking_context()
    )
    confirmation = services.appointment_booking.prepare_confirmation(
        workflow.workflow_id
    )

    first = services.appointment_booking.book(
        workflow.workflow_id,
        confirmation.selection_fingerprint,
        _confirm(),
    )
    second = services.appointment_booking.book(
        workflow.workflow_id,
        confirmation.selection_fingerprint,
        _confirm(),
    )

    assert second == first
    assert repositories.appointments.list_all() == [first]
    slot = repositories.slots.get(first.slot_id)
    assert slot is not None
    assert slot.version == 2


class FailingAppointmentRepository:
    def __init__(self, delegate):
        self._delegate = delegate

    def get(self, appointment_id):
        return self._delegate.get(appointment_id)

    def list_all(self):
        return self._delegate.list_all()

    def find_by_idempotency_key(self, idempotency_key):
        return self._delegate.find_by_idempotency_key(
            idempotency_key
        )

    def create_for_available_slot(
        self,
        appointment,
        expected_slot_version,
    ):
        raise RuntimeError("simulated ambiguous failure")


def test_ambiguous_booking_outcome_fails_closed():
    repositories, services, workflow, clock = (
        build_selected_booking_context()
    )
    booking = DefaultAppointmentBookingService(
        workflow_service=services.scheduling_workflows,
        provider_repository=repositories.providers,
        location_repository=repositories.provider_locations,
        slot_repository=repositories.slots,
        appointment_repository=FailingAppointmentRepository(
            repositories.appointments
        ),
        clock=clock,
    )
    confirmation = booking.prepare_confirmation(
        workflow.workflow_id
    )

    with pytest.raises(BookingOutcomeUnknown):
        booking.book(
            workflow.workflow_id,
            confirmation.selection_fingerprint,
            _confirm(),
        )

    assert repositories.appointments.list_all() == []
    assert services.scheduling_workflows.get(
        workflow.workflow_id
    ).state == WorkflowState.BOOKING
