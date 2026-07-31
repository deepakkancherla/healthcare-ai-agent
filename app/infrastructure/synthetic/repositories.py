from dataclasses import replace
from datetime import date
from threading import RLock
from typing import Any

from app.application.booking_errors import SlotReservationConflict
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


class InMemoryMemberRepository:
    def __init__(self, members: tuple[Member, ...]):
        self._members = {
            member.member_id: member for member in members
        }

    def get(self, member_id: str) -> Member | None:
        return self._members.get(member_id)


class InMemoryEnrollmentRepository:
    def __init__(self, enrollments: tuple[Enrollment, ...]):
        self._enrollments = enrollments

    def find_active(
        self,
        member_id: str,
        service_date: date,
    ) -> list[Enrollment]:
        return [
            enrollment
            for enrollment in self._enrollments
            if enrollment.member_id == member_id
            and enrollment.is_active_on(service_date)
        ]


class InMemoryHealthPlanRepository:
    def __init__(self, health_plans: tuple[HealthPlan, ...]):
        self._health_plans = {
            health_plan.health_plan_id: health_plan
            for health_plan in health_plans
        }

    def get(self, health_plan_id: str) -> HealthPlan | None:
        return self._health_plans.get(health_plan_id)


class InMemoryProviderNetworkRepository:
    def __init__(self, networks: tuple[ProviderNetwork, ...]):
        self._networks = {
            network.network_id: network for network in networks
        }

    def get(self, network_id: str) -> ProviderNetwork | None:
        return self._networks.get(network_id)


class InMemoryProviderRepository:
    def __init__(self, providers: tuple[Provider, ...]):
        self._providers = {
            provider.provider_id: provider for provider in providers
        }

    def get(self, provider_id: str) -> Provider | None:
        return self._providers.get(provider_id)

    def list_all(self) -> list[Provider]:
        return list(self._providers.values())


class InMemoryProviderLocationRepository:
    def __init__(self, locations: tuple[ProviderLocation, ...]):
        self._locations = {
            location.provider_location_id: location
            for location in locations
        }

    def get(
        self,
        provider_location_id: str,
    ) -> ProviderLocation | None:
        return self._locations.get(provider_location_id)

    def list_for_provider(
        self,
        provider_id: str,
    ) -> list[ProviderLocation]:
        return [
            location
            for location in self._locations.values()
            if location.provider_id == provider_id
        ]


class InMemoryNetworkParticipationRepository:
    def __init__(
        self,
        participations: tuple[NetworkParticipation, ...],
    ):
        self._participations = participations

    def find(
        self,
        network_id: str,
        provider_id: str,
        provider_location_id: str,
        specialty_or_service_code: str,
    ) -> list[NetworkParticipation]:
        expected_specialty = specialty_or_service_code.casefold()
        return [
            participation
            for participation in self._participations
            if participation.network_id == network_id
            and participation.provider_id == provider_id
            and (
                participation.provider_location_id
                == provider_location_id
            )
            and (
                participation.specialty_or_service_code.casefold()
                == expected_specialty
            )
        ]


class InMemorySlotRepository:
    def __init__(
        self,
        slots: tuple[AppointmentSlot, ...],
        lock: Any | None = None,
    ):
        self._slots = {slot.slot_id: slot for slot in slots}
        self._lock = lock or RLock()

    def get(self, slot_id: str) -> AppointmentSlot | None:
        with self._lock:
            return self._slots.get(slot_id)

    def list_all(self) -> list[AppointmentSlot]:
        with self._lock:
            return list(self._slots.values())

    def update(
        self,
        slot: AppointmentSlot,
        expected_version: int,
    ) -> None:
        with self._lock:
            current = self._slots.get(slot.slot_id)
            if current is None or current.version != expected_version:
                raise SlotReservationConflict(
                    "The appointment slot version changed."
                )
            self._slots[slot.slot_id] = slot


class InMemoryAppointmentRepository:
    def __init__(
        self,
        appointments: tuple[Appointment, ...],
        slot_repository: InMemorySlotRepository,
        lock: Any | None = None,
    ):
        self._appointments = {
            appointment.appointment_id: appointment
            for appointment in appointments
        }
        self._slots = slot_repository
        self._lock = lock or RLock()

    def get(self, appointment_id: str) -> Appointment | None:
        with self._lock:
            return self._appointments.get(appointment_id)

    def list_all(self) -> list[Appointment]:
        with self._lock:
            return list(self._appointments.values())

    def find_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Appointment | None:
        with self._lock:
            return next(
                (
                    appointment
                    for appointment in self._appointments.values()
                    if appointment.idempotency_key == idempotency_key
                ),
                None,
            )

    def create_for_available_slot(
        self,
        appointment: Appointment,
        expected_slot_version: int,
    ) -> Appointment:
        with self._lock:
            existing = self.find_by_idempotency_key(
                appointment.idempotency_key
            )
            if existing is not None:
                return existing

            slot = self._slots.get(appointment.slot_id)
            if (
                slot is None
                or slot.status != "available"
                or slot.version != expected_slot_version
            ):
                raise SlotReservationConflict(
                    "The appointment slot is no longer available."
                )
            if appointment.appointment_id in self._appointments:
                raise RuntimeError("Appointment identifier already exists.")

            self._slots.update(
                replace(
                    slot,
                    status="booked",
                    version=slot.version + 1,
                ),
                expected_version=slot.version,
            )
            self._appointments[
                appointment.appointment_id
            ] = appointment
            return appointment


class WorkflowVersionConflict(RuntimeError):
    """Raised when workflow optimistic concurrency validation fails."""


class InMemoryWorkflowRepository:
    def __init__(
        self,
        workflows: tuple[SchedulingWorkflow, ...] = (),
    ):
        self._workflows = {
            workflow.workflow_id: workflow for workflow in workflows
        }

    def get(self, workflow_id: str) -> SchedulingWorkflow | None:
        return self._workflows.get(workflow_id)

    def find_by_conversation(
        self,
        member_id: str,
        conversation_id: str,
    ) -> SchedulingWorkflow | None:
        return next(
            (
                workflow
                for workflow in self._workflows.values()
                if workflow.member_id == member_id
                and workflow.conversation_id == conversation_id
            ),
            None,
        )

    def save(
        self,
        workflow: SchedulingWorkflow,
        expected_version: int | None,
    ) -> None:
        existing = self._workflows.get(workflow.workflow_id)
        if expected_version is None:
            if existing is not None:
                raise WorkflowVersionConflict(
                    "Scheduling workflow already exists."
                )
        elif existing is None or existing.version != expected_version:
            raise WorkflowVersionConflict(
                "Scheduling workflow version does not match."
            )

        self._workflows[workflow.workflow_id] = workflow
