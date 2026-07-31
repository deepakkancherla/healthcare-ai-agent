from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
import hmac

from app.application.ports import SlotRepository, WorkflowRepository
from app.application.booking_errors import (
    ConfirmationExpired,
    ConfirmationFingerprintMismatch,
    ConfirmationNotPrepared,
    ExplicitConfirmationRequired,
    InvalidBookingState,
)
from app.domain.models import (
    AppointmentSelection,
    AppointmentSlot,
    AvailabilityQuery,
    BookingConfirmation,
    ExplicitConfirmation,
    NetworkStatus,
    NetworkVerificationResult,
    ProviderCandidate,
    ProviderReference,
    ProviderSearchCriteria,
    SchedulingWorkflow,
    WorkflowState,
)


class SlotNotFoundError(LookupError):
    """Raised when an appointment slot does not exist."""


class WorkflowNotFoundError(LookupError):
    """Raised when a scheduling workflow does not exist."""


class InvalidWorkflowTransition(ValueError):
    """Raised when a command is invalid for the current workflow state."""


class DefaultAvailabilityService:
    def __init__(self, slot_repository: SlotRepository):
        self._slots = slot_repository

    def search(
        self,
        query: AvailabilityQuery,
    ) -> list[AppointmentSlot]:
        matches = [
            slot
            for slot in self._slots.list_all()
            if slot.provider_id == query.provider_id
            and (
                slot.provider_location_id
                == query.provider_location_id
            )
            and query.start_date
            <= slot.start_at.date()
            <= query.end_date
            and slot.status == "available"
            and (
                query.modality is None
                or slot.modality.casefold() == query.modality.casefold()
            )
        ]
        return sorted(matches, key=lambda slot: slot.start_at)

    def get_current_slot(self, slot_id: str) -> AppointmentSlot:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise SlotNotFoundError(
                f"Appointment slot '{slot_id}' was not found."
            )
        return slot


class DefaultSchedulingWorkflowService:
    _ALLOWED_TRANSITIONS = {
        WorkflowState.COLLECTING_REQUIREMENTS: {
            WorkflowState.SEARCHING_PROVIDERS,
        },
        WorkflowState.SEARCHING_PROVIDERS: {
            WorkflowState.VERIFYING_NETWORK,
            WorkflowState.COLLECTING_REQUIREMENTS,
        },
        WorkflowState.VERIFYING_NETWORK: {
            WorkflowState.SEARCHING_AVAILABILITY,
            WorkflowState.COLLECTING_REQUIREMENTS,
        },
        WorkflowState.SEARCHING_AVAILABILITY: {
            WorkflowState.PRESENTING_OPTIONS,
            WorkflowState.COLLECTING_REQUIREMENTS,
        },
        WorkflowState.PRESENTING_OPTIONS: {
            WorkflowState.AWAITING_SELECTION,
        },
        WorkflowState.AWAITING_SELECTION: {
            WorkflowState.AWAITING_CONFIRMATION,
        },
        WorkflowState.AWAITING_CONFIRMATION: {
            WorkflowState.AWAITING_SELECTION,
            WorkflowState.BOOKING,
        },
        WorkflowState.BOOKING: {
            WorkflowState.CONFIRMED,
            WorkflowState.SEARCHING_AVAILABILITY,
            WorkflowState.FAILED,
        },
    }

    def __init__(
        self,
        workflow_repository: WorkflowRepository,
        clock: Callable[[], datetime] | None = None,
    ):
        self._workflows = workflow_repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def start_or_resume(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow:
        existing = self._workflows.find_by_conversation(
            member_id,
            conversation_id,
        )
        if existing is not None:
            return existing

        now = self._clock()
        workflow = SchedulingWorkflow(
            workflow_id=f"workflow-{member_id}-{conversation_id}",
            member_id=member_id,
            conversation_id=conversation_id,
            state=WorkflowState.COLLECTING_REQUIREMENTS,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._workflows.save(workflow, expected_version=None)
        return workflow

    def get(self, workflow_id: str) -> SchedulingWorkflow:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(
                f"Scheduling workflow '{workflow_id}' was not found."
            )
        return workflow

    def get_for_conversation(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow | None:
        return self._workflows.find_by_conversation(
            member_id,
            conversation_id,
        )

    def record_provider_search(
        self,
        member_id: str,
        conversation_id: str,
        criteria: ProviderSearchCriteria,
        candidates: list[ProviderCandidate],
    ) -> SchedulingWorkflow:
        workflow = self.start_or_resume(member_id, conversation_id)
        workflow = self._transition(
            workflow,
            WorkflowState.SEARCHING_PROVIDERS,
            search_criteria=criteria,
            provider_candidates=(),
            network_result=None,
            availability_query=None,
            available_slot_ids=(),
            selection=None,
            confirmation=None,
            appointment_id=None,
        )

        references = tuple(
            ProviderReference(
                provider_id=candidate.provider.provider_id,
                provider_location_id=(
                    candidate.location.provider_location_id
                ),
            )
            for candidate in candidates
        )
        target_state = (
            WorkflowState.VERIFYING_NETWORK
            if references
            else WorkflowState.COLLECTING_REQUIREMENTS
        )
        return self._transition(
            workflow,
            target_state,
            provider_candidates=references,
        )

    def record_network_verification(
        self,
        workflow_id: str,
        result: NetworkVerificationResult,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        reference = ProviderReference(
            provider_id=result.provider_id,
            provider_location_id=result.provider_location_id,
        )
        if reference not in workflow.provider_candidates:
            raise InvalidWorkflowTransition(
                "Network verification must reference a provider candidate."
            )

        target_state = (
            WorkflowState.SEARCHING_AVAILABILITY
            if result.status == NetworkStatus.IN_NETWORK
            else WorkflowState.COLLECTING_REQUIREMENTS
        )
        return self._transition(
            workflow,
            target_state,
            network_result=result,
        )

    def record_network_failure(
        self,
        workflow_id: str,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        return self._transition(
            workflow,
            WorkflowState.COLLECTING_REQUIREMENTS,
            network_result=None,
        )

    def record_availability(
        self,
        workflow_id: str,
        query: AvailabilityQuery,
        slots: list[AppointmentSlot],
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        network_result = workflow.network_result
        if (
            network_result is None
            or query.provider_id != network_result.provider_id
            or query.provider_location_id
            != network_result.provider_location_id
        ):
            raise InvalidWorkflowTransition(
                "Availability must match the verified provider and location."
            )

        for slot in slots:
            if (
                slot.provider_id != query.provider_id
                or slot.provider_location_id
                != query.provider_location_id
                or slot.status != "available"
            ):
                raise InvalidWorkflowTransition(
                    "Availability results do not match the active query."
                )

        if not slots:
            return self._transition(
                workflow,
                WorkflowState.COLLECTING_REQUIREMENTS,
                availability_query=query,
                available_slot_ids=(),
            )

        workflow = self._transition(
            workflow,
            WorkflowState.PRESENTING_OPTIONS,
            availability_query=query,
            available_slot_ids=tuple(slot.slot_id for slot in slots),
        )
        return self._transition(
            workflow,
            WorkflowState.AWAITING_SELECTION,
        )

    def select_slot(
        self,
        workflow_id: str,
        slot: AppointmentSlot,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        network_result = workflow.network_result
        if slot.slot_id not in workflow.available_slot_ids:
            raise InvalidWorkflowTransition(
                "The selected slot was not presented by this workflow."
            )
        if slot.status != "available":
            raise InvalidWorkflowTransition(
                "The selected slot is no longer available."
            )
        if (
            network_result is None
            or network_result.status != NetworkStatus.IN_NETWORK
            or network_result.source_reference is None
            or slot.provider_id != network_result.provider_id
            or slot.provider_location_id
            != network_result.provider_location_id
        ):
            raise InvalidWorkflowTransition(
                "The selected slot does not match network verification."
            )

        selection = AppointmentSelection(
            slot_id=slot.slot_id,
            slot_version=slot.version,
            member_id=workflow.member_id,
            workflow_id=workflow.workflow_id,
            provider_id=slot.provider_id,
            provider_location_id=slot.provider_location_id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            time_zone=slot.time_zone,
            modality=slot.modality,
            network_status=network_result.status,
            health_plan_id=network_result.health_plan_id,
            network_id=network_result.network_id,
            network_source_reference=network_result.source_reference,
            network_service_date=network_result.service_date,
        )
        return self._transition(
            workflow,
            WorkflowState.AWAITING_CONFIRMATION,
            selection=selection,
            confirmation=None,
            appointment_id=None,
        )

    def store_confirmation(
        self,
        workflow_id: str,
        confirmation: BookingConfirmation,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        if workflow.state != WorkflowState.AWAITING_CONFIRMATION:
            raise InvalidBookingState(
                "A confirmation can only be prepared while awaiting "
                "confirmation."
            )
        if workflow.selection is None:
            raise ConfirmationNotPrepared(
                "The workflow does not contain an appointment selection."
            )
        if confirmation.workflow_id != workflow.workflow_id:
            raise ConfirmationFingerprintMismatch(
                "The confirmation does not belong to this workflow."
            )

        return self._persist(
            workflow,
            confirmation=confirmation,
        )

    def begin_booking(
        self,
        workflow_id: str,
        confirmation_fingerprint: str,
        explicit_confirmation: ExplicitConfirmation,
        confirmed_at: datetime,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        if workflow.state != WorkflowState.AWAITING_CONFIRMATION:
            raise InvalidBookingState(
                "Booking is allowed only while awaiting confirmation."
            )
        if not explicit_confirmation.confirmed:
            raise ExplicitConfirmationRequired(
                "The member must explicitly confirm the appointment."
            )

        confirmation = workflow.confirmation
        if confirmation is None:
            raise ConfirmationNotPrepared(
                "A booking confirmation summary has not been prepared."
            )
        if not hmac.compare_digest(
            confirmation.selection_fingerprint,
            confirmation_fingerprint,
        ):
            raise ConfirmationFingerprintMismatch(
                "The confirmation fingerprint does not match."
            )
        if confirmed_at >= confirmation.expires_at:
            self._transition(
                workflow,
                WorkflowState.AWAITING_SELECTION,
                selection=None,
                confirmation=None,
            )
            raise ConfirmationExpired(
                "The appointment confirmation has expired."
            )

        return self._transition(
            workflow,
            WorkflowState.BOOKING,
        )

    def mark_slot_unavailable(
        self,
        workflow_id: str,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        return self._transition(
            workflow,
            WorkflowState.SEARCHING_AVAILABILITY,
            available_slot_ids=(),
            selection=None,
            confirmation=None,
        )

    def mark_booking_confirmed(
        self,
        workflow_id: str,
        appointment_id: str,
    ) -> SchedulingWorkflow:
        workflow = self.get(workflow_id)
        return self._transition(
            workflow,
            WorkflowState.CONFIRMED,
            appointment_id=appointment_id,
        )

    def _transition(
        self,
        workflow: SchedulingWorkflow,
        target_state: WorkflowState,
        **changes,
    ) -> SchedulingWorkflow:
        allowed = self._ALLOWED_TRANSITIONS.get(workflow.state, set())
        if target_state not in allowed:
            raise InvalidWorkflowTransition(
                "Cannot transition scheduling workflow from "
                f"{workflow.state.value} to {target_state.value}."
            )

        updated = replace(
            workflow,
            state=target_state,
            version=workflow.version + 1,
            updated_at=self._clock(),
            **changes,
        )
        self._workflows.save(
            updated,
            expected_version=workflow.version,
        )
        return updated

    def _persist(
        self,
        workflow: SchedulingWorkflow,
        **changes,
    ) -> SchedulingWorkflow:
        updated = replace(
            workflow,
            version=workflow.version + 1,
            updated_at=self._clock(),
            **changes,
        )
        self._workflows.save(
            updated,
            expected_version=workflow.version,
        )
        return updated
