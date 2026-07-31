from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock

from app.application.service_interfaces import (
    AppointmentBookingService,
    AvailabilityService,
    MemberProfileService,
    NetworkVerificationService,
    ProviderDirectoryService,
    SchedulingWorkflowService,
)
from app.application.booking_services import (
    DefaultAppointmentBookingService,
)
from app.application.ports import (
    AppointmentRepository,
    EnrollmentRepository,
    HealthPlanRepository,
    MemberRepository,
    NetworkParticipationRepository,
    ProviderLocationRepository,
    ProviderNetworkRepository,
    ProviderRepository,
    SlotRepository,
    WorkflowRepository,
)
from app.application.scheduling_services import (
    DefaultAvailabilityService,
    DefaultSchedulingWorkflowService,
)
from app.application.services import (
    DefaultMemberProfileService,
    DefaultNetworkVerificationService,
    DefaultProviderDirectoryService,
)
from app.infrastructure.synthetic.fixtures.v1 import (
    APPOINTMENTS,
    ENROLLMENTS,
    HEALTH_PLANS,
    MEMBERS,
    NETWORK_PARTICIPATIONS,
    NETWORKS,
    PROVIDER_LOCATIONS,
    PROVIDERS,
    SLOTS,
)
from app.infrastructure.synthetic.repositories import (
    InMemoryAppointmentRepository,
    InMemoryEnrollmentRepository,
    InMemoryHealthPlanRepository,
    InMemoryMemberRepository,
    InMemoryNetworkParticipationRepository,
    InMemoryProviderLocationRepository,
    InMemoryProviderNetworkRepository,
    InMemoryProviderRepository,
    InMemorySlotRepository,
    InMemoryWorkflowRepository,
)


@dataclass(frozen=True)
class SyntheticRepositories:
    members: MemberRepository
    enrollments: EnrollmentRepository
    health_plans: HealthPlanRepository
    networks: ProviderNetworkRepository
    providers: ProviderRepository
    provider_locations: ProviderLocationRepository
    network_participations: NetworkParticipationRepository
    slots: SlotRepository
    appointments: AppointmentRepository
    workflows: WorkflowRepository


@dataclass(frozen=True)
class HealthcareServices:
    member_profiles: MemberProfileService
    provider_directory: ProviderDirectoryService
    network_verification: NetworkVerificationService
    availability: AvailabilityService
    scheduling_workflows: SchedulingWorkflowService
    appointment_booking: AppointmentBookingService


def build_synthetic_repositories() -> SyntheticRepositories:
    booking_lock = RLock()
    slot_repository = InMemorySlotRepository(
        SLOTS,
        lock=booking_lock,
    )
    appointment_repository = InMemoryAppointmentRepository(
        APPOINTMENTS,
        slot_repository=slot_repository,
        lock=booking_lock,
    )
    return SyntheticRepositories(
        members=InMemoryMemberRepository(MEMBERS),
        enrollments=InMemoryEnrollmentRepository(ENROLLMENTS),
        health_plans=InMemoryHealthPlanRepository(HEALTH_PLANS),
        networks=InMemoryProviderNetworkRepository(NETWORKS),
        providers=InMemoryProviderRepository(PROVIDERS),
        provider_locations=InMemoryProviderLocationRepository(
            PROVIDER_LOCATIONS
        ),
        network_participations=(
            InMemoryNetworkParticipationRepository(
                NETWORK_PARTICIPATIONS
            )
        ),
        slots=slot_repository,
        appointments=appointment_repository,
        workflows=InMemoryWorkflowRepository(),
    )


def build_synthetic_services(
    repositories: SyntheticRepositories | None = None,
    clock: Callable[[], datetime] | None = None,
    confirmation_ttl: timedelta = timedelta(minutes=10),
) -> HealthcareServices:
    repositories = repositories or build_synthetic_repositories()

    scheduling_workflows = DefaultSchedulingWorkflowService(
        workflow_repository=repositories.workflows,
        clock=clock,
    )
    return HealthcareServices(
        member_profiles=DefaultMemberProfileService(
            member_repository=repositories.members,
            enrollment_repository=repositories.enrollments,
            health_plan_repository=repositories.health_plans,
            network_repository=repositories.networks,
        ),
        provider_directory=DefaultProviderDirectoryService(
            provider_repository=repositories.providers,
            location_repository=repositories.provider_locations,
        ),
        network_verification=DefaultNetworkVerificationService(
            participation_repository=(
                repositories.network_participations
            ),
        ),
        availability=DefaultAvailabilityService(
            slot_repository=repositories.slots,
        ),
        scheduling_workflows=scheduling_workflows,
        appointment_booking=DefaultAppointmentBookingService(
            workflow_service=scheduling_workflows,
            provider_repository=repositories.providers,
            location_repository=repositories.provider_locations,
            slot_repository=repositories.slots,
            appointment_repository=repositories.appointments,
            clock=clock,
            confirmation_ttl=confirmation_ttl,
        ),
    )
