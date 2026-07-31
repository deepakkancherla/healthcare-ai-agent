from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

from app.application.booking_errors import (
    BookingOutcomeUnknown,
    ExplicitConfirmationRequired,
    InvalidBookingState,
    SlotReservationConflict,
)
from app.application.ports import (
    AppointmentRepository,
    ProviderLocationRepository,
    ProviderRepository,
    SlotRepository,
)
from app.application.service_interfaces import (
    SchedulingWorkflowService,
)
from app.domain.models import (
    Appointment,
    BookingConfirmation,
    ConfirmationSummary,
    ExplicitConfirmation,
    SchedulingWorkflow,
    WorkflowState,
)


class DefaultAppointmentBookingService:
    def __init__(
        self,
        workflow_service: SchedulingWorkflowService,
        provider_repository: ProviderRepository,
        location_repository: ProviderLocationRepository,
        slot_repository: SlotRepository,
        appointment_repository: AppointmentRepository,
        clock: Callable[[], datetime] | None = None,
        confirmation_ttl: timedelta = timedelta(minutes=10),
    ):
        self._workflows = workflow_service
        self._providers = provider_repository
        self._locations = location_repository
        self._slots = slot_repository
        self._appointments = appointment_repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._confirmation_ttl = confirmation_ttl

    def prepare_confirmation(
        self,
        workflow_id: str,
    ) -> BookingConfirmation:
        workflow = self._workflows.get(workflow_id)
        selection = workflow.selection
        criteria = workflow.search_criteria
        if (
            workflow.state != WorkflowState.AWAITING_CONFIRMATION
            or selection is None
            or criteria is None
        ):
            raise InvalidBookingState(
                "Confirmation requires an exact selected appointment."
            )

        provider = self._providers.get(selection.provider_id)
        location = self._locations.get(
            selection.provider_location_id
        )
        if (
            provider is None
            or location is None
            or location.provider_id != provider.provider_id
        ):
            raise InvalidBookingState(
                "The selected provider details are unavailable."
            )

        summary = ConfirmationSummary(
            provider_name=provider.display_name,
            specialty=criteria.specialty,
            location=(
                f"{location.address}, {location.city}, "
                f"{location.state} {location.postal_code}"
            ),
            start_at=selection.start_at,
            end_at=selection.end_at,
            time_zone=selection.time_zone,
            modality=selection.modality,
            network_status=selection.network_status,
            limitations=(
                "Synthetic scheduling data only.",
                (
                    "In-network participation does not guarantee "
                    "coverage or member cost."
                ),
            ),
        )
        fingerprint = self._selection_fingerprint(
            workflow,
            summary,
        )
        presented_at = self._clock()
        confirmation = BookingConfirmation(
            workflow_id=workflow.workflow_id,
            selection_fingerprint=fingerprint,
            summary=summary,
            presented_at=presented_at,
            expires_at=presented_at + self._confirmation_ttl,
        )
        persisted = self._workflows.store_confirmation(
            workflow.workflow_id,
            confirmation,
        )
        if persisted.confirmation is None:
            raise BookingOutcomeUnknown(
                "The confirmation could not be persisted."
            )
        return persisted.confirmation

    def book(
        self,
        workflow_id: str,
        confirmation_fingerprint: str,
        explicit_confirmation: ExplicitConfirmation,
    ) -> Appointment:
        workflow = self._workflows.get(workflow_id)
        idempotency_key = self._idempotency_key(
            workflow_id,
            confirmation_fingerprint,
        )
        existing = self._appointments.find_by_idempotency_key(
            idempotency_key
        )
        if existing is not None:
            self._validate_duplicate_confirmation(
                workflow,
                confirmation_fingerprint,
                explicit_confirmation,
            )
            if workflow.state == WorkflowState.BOOKING:
                self._workflows.mark_booking_confirmed(
                    workflow_id,
                    existing.appointment_id,
                )
            return existing

        workflow = self._workflows.begin_booking(
            workflow_id=workflow_id,
            confirmation_fingerprint=confirmation_fingerprint,
            explicit_confirmation=explicit_confirmation,
            confirmed_at=self._clock(),
        )
        selection = workflow.selection
        if selection is None:
            raise BookingOutcomeUnknown(
                "The booking selection could not be established."
            )

        current_slot = self._slots.get(selection.slot_id)
        if (
            current_slot is None
            or current_slot.status != "available"
            or current_slot.version != selection.slot_version
            or current_slot.provider_id != selection.provider_id
            or current_slot.provider_location_id
            != selection.provider_location_id
            or current_slot.start_at != selection.start_at
            or current_slot.end_at != selection.end_at
            or current_slot.time_zone != selection.time_zone
            or current_slot.modality != selection.modality
        ):
            self._workflows.mark_slot_unavailable(workflow_id)
            raise SlotReservationConflict(
                "The selected appointment slot is no longer available."
            )

        appointment = self._build_appointment(
            workflow,
            idempotency_key,
        )
        try:
            persisted = (
                self._appointments.create_for_available_slot(
                    appointment,
                    expected_slot_version=selection.slot_version,
                )
            )
        except SlotReservationConflict:
            self._workflows.mark_slot_unavailable(workflow_id)
            raise
        except Exception as error:
            reconciled = (
                self._appointments.find_by_idempotency_key(
                    idempotency_key
                )
            )
            if reconciled is None:
                raise BookingOutcomeUnknown(
                    "The booking outcome could not be established."
                ) from error
            persisted = reconciled

        try:
            current_workflow = self._workflows.get(workflow_id)
            if current_workflow.state != WorkflowState.CONFIRMED:
                self._workflows.mark_booking_confirmed(
                    workflow_id,
                    persisted.appointment_id,
                )
        except Exception as error:
            raise BookingOutcomeUnknown(
                "The booking was created but workflow reconciliation "
                "did not complete."
            ) from error

        return persisted

    def _validate_duplicate_confirmation(
        self,
        workflow: SchedulingWorkflow,
        confirmation_fingerprint: str,
        explicit_confirmation: ExplicitConfirmation,
    ) -> None:
        confirmation = workflow.confirmation
        if not explicit_confirmation.confirmed:
            raise ExplicitConfirmationRequired(
                "Repeated booking requires explicit confirmation."
            )
        if (
            workflow.state
            not in {WorkflowState.BOOKING, WorkflowState.CONFIRMED}
            or confirmation is None
            or not hmac.compare_digest(
                confirmation.selection_fingerprint,
                confirmation_fingerprint,
            )
        ):
            raise InvalidBookingState(
                "The existing appointment does not match this "
                "confirmation."
            )

    def _build_appointment(
        self,
        workflow: SchedulingWorkflow,
        idempotency_key: str,
    ) -> Appointment:
        selection = workflow.selection
        if selection is None:
            raise BookingOutcomeUnknown(
                "The booking selection could not be established."
            )

        return Appointment(
            appointment_id=f"appointment-{idempotency_key[:16]}",
            member_id=workflow.member_id,
            slot_id=selection.slot_id,
            status="confirmed",
            confirmation_number=(
                f"SYN-{idempotency_key[:10].upper()}"
            ),
            idempotency_key=idempotency_key,
            created_at=self._clock(),
        )

    @staticmethod
    def _idempotency_key(
        workflow_id: str,
        confirmation_fingerprint: str,
    ) -> str:
        value = f"{workflow_id}:{confirmation_fingerprint}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _selection_fingerprint(
        workflow: SchedulingWorkflow,
        summary: ConfirmationSummary,
    ) -> str:
        selection = workflow.selection
        if selection is None:
            raise InvalidBookingState(
                "The workflow does not contain a selection."
            )

        payload = {
            "workflow_id": workflow.workflow_id,
            "member_id": workflow.member_id,
            "slot_id": selection.slot_id,
            "slot_version": selection.slot_version,
            "provider_id": selection.provider_id,
            "provider_location_id": (
                selection.provider_location_id
            ),
            "provider_name": summary.provider_name,
            "specialty": summary.specialty,
            "location": summary.location,
            "start_at": selection.start_at.isoformat(),
            "end_at": selection.end_at.isoformat(),
            "time_zone": selection.time_zone,
            "modality": selection.modality,
            "network_status": selection.network_status.value,
            "health_plan_id": selection.health_plan_id,
            "network_id": selection.network_id,
            "network_source_reference": (
                selection.network_source_reference
            ),
            "network_service_date": (
                selection.network_service_date.isoformat()
            ),
            "limitations": list(summary.limitations),
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
