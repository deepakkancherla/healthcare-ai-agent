from dataclasses import dataclass

from app.application.service_interfaces import (
    MemberProfileService,
    NetworkVerificationService,
    ProviderDirectoryService,
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


@dataclass(frozen=True)
class HealthcareServices:
    member_profiles: MemberProfileService
    provider_directory: ProviderDirectoryService
    network_verification: NetworkVerificationService


def build_synthetic_repositories() -> SyntheticRepositories:
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
        slots=InMemorySlotRepository(SLOTS),
        appointments=InMemoryAppointmentRepository(APPOINTMENTS),
    )


def build_synthetic_services(
    repositories: SyntheticRepositories | None = None,
) -> HealthcareServices:
    repositories = repositories or build_synthetic_repositories()

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
    )
