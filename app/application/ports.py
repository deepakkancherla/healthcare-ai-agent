from datetime import date
from typing import Protocol

from app.domain.models import (
    Appointment,
    AppointmentSlot,
    Enrollment,
    HealthPlan,
    Member,
    NetworkParticipation,
    Provider,
    ProviderLocation,
    ProviderNetwork,
    SchedulingWorkflow,
)


class MemberRepository(Protocol):
    def get(self, member_id: str) -> Member | None: ...


class EnrollmentRepository(Protocol):
    def find_active(
        self,
        member_id: str,
        service_date: date,
    ) -> list[Enrollment]: ...


class HealthPlanRepository(Protocol):
    def get(self, health_plan_id: str) -> HealthPlan | None: ...


class ProviderNetworkRepository(Protocol):
    def get(self, network_id: str) -> ProviderNetwork | None: ...


class ProviderRepository(Protocol):
    def get(self, provider_id: str) -> Provider | None: ...

    def list_all(self) -> list[Provider]: ...


class ProviderLocationRepository(Protocol):
    def get(
        self,
        provider_location_id: str,
    ) -> ProviderLocation | None: ...

    def list_for_provider(
        self,
        provider_id: str,
    ) -> list[ProviderLocation]: ...


class NetworkParticipationRepository(Protocol):
    def find(
        self,
        network_id: str,
        provider_id: str,
        provider_location_id: str,
        specialty_or_service_code: str,
    ) -> list[NetworkParticipation]: ...


class SlotRepository(Protocol):
    def get(self, slot_id: str) -> AppointmentSlot | None: ...

    def list_all(self) -> list[AppointmentSlot]: ...

    def update(
        self,
        slot: AppointmentSlot,
        expected_version: int,
    ) -> None: ...


class AppointmentRepository(Protocol):
    def get(self, appointment_id: str) -> Appointment | None: ...

    def list_all(self) -> list[Appointment]: ...

    def find_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Appointment | None: ...

    def create_for_available_slot(
        self,
        appointment: Appointment,
        expected_slot_version: int,
    ) -> Appointment: ...


class WorkflowRepository(Protocol):
    def get(self, workflow_id: str) -> SchedulingWorkflow | None: ...

    def find_by_conversation(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow | None: ...

    def save(
        self,
        workflow: SchedulingWorkflow,
        expected_version: int | None,
    ) -> None: ...
