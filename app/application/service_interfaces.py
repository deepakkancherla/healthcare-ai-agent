from datetime import date
from typing import Protocol

from app.domain.models import (
    AppointmentSlot,
    AvailabilityQuery,
    MemberCoverageContext,
    NetworkVerificationResult,
    ProviderCandidate,
    ProviderSearchCriteria,
    SchedulingWorkflow,
)


class MemberProfileService(Protocol):
    def get_member_context(
        self,
        member_id: str,
        service_date: date,
    ) -> MemberCoverageContext: ...


class ProviderDirectoryService(Protocol):
    def search(
        self,
        criteria: ProviderSearchCriteria,
    ) -> list[ProviderCandidate]: ...

    def resolve(
        self,
        provider_name: str,
        provider_location: str | None = None,
        specialty: str | None = None,
    ) -> ProviderCandidate | None: ...


class NetworkVerificationService(Protocol):
    def verify(
        self,
        coverage: MemberCoverageContext,
        provider_id: str,
        provider_location_id: str,
        specialty_or_service_code: str,
        service_date: date,
    ) -> NetworkVerificationResult: ...


class AvailabilityService(Protocol):
    def search(
        self,
        query: AvailabilityQuery,
    ) -> list[AppointmentSlot]: ...

    def get_current_slot(self, slot_id: str) -> AppointmentSlot: ...


class SchedulingWorkflowService(Protocol):
    def start_or_resume(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow: ...

    def get(self, workflow_id: str) -> SchedulingWorkflow: ...

    def get_for_conversation(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow | None: ...

    def record_provider_search(
        self,
        member_id: str,
        conversation_id: str,
        criteria: ProviderSearchCriteria,
        candidates: list[ProviderCandidate],
    ) -> SchedulingWorkflow: ...

    def record_network_verification(
        self,
        workflow_id: str,
        result: NetworkVerificationResult,
    ) -> SchedulingWorkflow: ...

    def record_network_failure(
        self,
        workflow_id: str,
    ) -> SchedulingWorkflow: ...

    def record_availability(
        self,
        workflow_id: str,
        query: AvailabilityQuery,
        slots: list[AppointmentSlot],
    ) -> SchedulingWorkflow: ...

    def select_slot(
        self,
        workflow_id: str,
        slot: AppointmentSlot,
    ) -> SchedulingWorkflow: ...
