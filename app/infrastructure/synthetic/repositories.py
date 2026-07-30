from datetime import date

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
    def __init__(self, slots: tuple[AppointmentSlot, ...]):
        self._slots = {slot.slot_id: slot for slot in slots}

    def get(self, slot_id: str) -> AppointmentSlot | None:
        return self._slots.get(slot_id)

    def list_all(self) -> list[AppointmentSlot]:
        return list(self._slots.values())


class InMemoryAppointmentRepository:
    def __init__(self, appointments: tuple[Appointment, ...]):
        self._appointments = {
            appointment.appointment_id: appointment
            for appointment in appointments
        }

    def get(self, appointment_id: str) -> Appointment | None:
        return self._appointments.get(appointment_id)

    def list_all(self) -> list[Appointment]:
        return list(self._appointments.values())


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
