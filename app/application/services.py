from datetime import date

from app.application.ports import (
    EnrollmentRepository,
    HealthPlanRepository,
    MemberRepository,
    NetworkParticipationRepository,
    ProviderLocationRepository,
    ProviderNetworkRepository,
    ProviderRepository,
)
from app.domain.models import (
    MemberCoverageContext,
    NetworkStatus,
    NetworkVerificationResult,
    ProviderCandidate,
    ProviderSearchCriteria,
)


class MemberContextError(ValueError):
    """Raised when an authoritative member coverage context cannot be built."""


class DefaultMemberProfileService:
    def __init__(
        self,
        member_repository: MemberRepository,
        enrollment_repository: EnrollmentRepository,
        health_plan_repository: HealthPlanRepository,
        network_repository: ProviderNetworkRepository,
    ):
        self._members = member_repository
        self._enrollments = enrollment_repository
        self._health_plans = health_plan_repository
        self._networks = network_repository

    def get_member_context(
        self,
        member_id: str,
        service_date: date,
    ) -> MemberCoverageContext:
        member = self._members.get(member_id)
        if member is None or member.status != "active":
            raise MemberContextError("Active member was not found.")

        enrollments = self._enrollments.find_active(
            member_id,
            service_date,
        )
        if len(enrollments) != 1:
            raise MemberContextError(
                "Exactly one active enrollment is required."
            )

        enrollment = enrollments[0]
        health_plan = self._health_plans.get(enrollment.health_plan_id)
        if health_plan is None:
            raise MemberContextError("Health plan was not found.")

        network = self._networks.get(health_plan.network_id)
        if network is None or not network.is_active_on(service_date):
            raise MemberContextError("Active provider network was not found.")

        return MemberCoverageContext(
            member=member,
            enrollment=enrollment,
            health_plan=health_plan,
            network=network,
        )


class DefaultProviderDirectoryService:
    def __init__(
        self,
        provider_repository: ProviderRepository,
        location_repository: ProviderLocationRepository,
    ):
        self._providers = provider_repository
        self._locations = location_repository

    def search(
        self,
        criteria: ProviderSearchCriteria,
    ) -> list[ProviderCandidate]:
        expected_location = criteria.location.casefold()
        expected_specialty = criteria.specialty.casefold()
        expected_gender = (
            criteria.gender.casefold()
            if criteria.gender is not None
            else None
        )
        matches: list[ProviderCandidate] = []

        for provider in self._providers.list_all():
            if not provider.active:
                continue

            matched_specialty = next(
                (
                    specialty
                    for specialty in provider.specialty_codes
                    if specialty.casefold() == expected_specialty
                ),
                None,
            )
            if matched_specialty is None:
                continue

            if (
                expected_gender is not None
                and provider.gender.casefold() != expected_gender
            ):
                continue

            for location in self._locations.list_for_provider(
                provider.provider_id
            ):
                if (
                    location.active
                    and (
                        location.city.casefold() == expected_location
                        or expected_location
                        in location.address.casefold()
                    )
                ):
                    matches.append(
                        ProviderCandidate(
                            provider=provider,
                            location=location,
                            matched_specialty=matched_specialty,
                        )
                    )

        return sorted(
            matches,
            key=lambda match: (
                match.provider.display_name,
                match.location.city,
            ),
        )

    def resolve(
        self,
        provider_name: str,
        provider_location: str | None = None,
        specialty: str | None = None,
    ) -> ProviderCandidate | None:
        expected_name = provider_name.casefold()
        expected_location = (
            provider_location.casefold()
            if provider_location is not None
            else None
        )
        expected_specialty = (
            specialty.casefold() if specialty is not None else None
        )

        for provider in self._providers.list_all():
            if (
                not provider.active
                or provider.display_name.casefold() != expected_name
            ):
                continue

            matched_specialty = next(
                (
                    value
                    for value in provider.specialty_codes
                    if expected_specialty is None
                    or value.casefold() == expected_specialty
                ),
                None,
            )
            if matched_specialty is None:
                continue

            for location in self._locations.list_for_provider(
                provider.provider_id
            ):
                if not location.active:
                    continue
                if (
                    expected_location is None
                    or location.city.casefold() == expected_location
                    or expected_location in location.address.casefold()
                ):
                    return ProviderCandidate(
                        provider=provider,
                        location=location,
                        matched_specialty=matched_specialty,
                    )

        return None


class DefaultNetworkVerificationService:
    def __init__(
        self,
        participation_repository: NetworkParticipationRepository,
    ):
        self._participations = participation_repository

    def verify(
        self,
        coverage: MemberCoverageContext,
        provider_id: str,
        provider_location_id: str,
        specialty_or_service_code: str,
        service_date: date,
    ) -> NetworkVerificationResult:
        if (
            not coverage.enrollment.is_active_on(service_date)
            or not coverage.network.is_active_on(service_date)
        ):
            return NetworkVerificationResult(
                status=NetworkStatus.UNKNOWN,
                member_id=coverage.member.member_id,
                health_plan_id=coverage.health_plan.health_plan_id,
                network_id=coverage.network.network_id,
                provider_id=provider_id,
                provider_location_id=provider_location_id,
                specialty_or_service_code=specialty_or_service_code,
                service_date=service_date,
                source_reference=None,
                reason=(
                    "Member coverage is not active on the service date."
                ),
            )

        participations = self._participations.find(
            network_id=coverage.network.network_id,
            provider_id=provider_id,
            provider_location_id=provider_location_id,
            specialty_or_service_code=specialty_or_service_code,
        )
        active_records = [
            participation
            for participation in participations
            if participation.is_active_on(service_date)
        ]

        if len(active_records) != 1:
            reason = (
                "No active participation record was found."
                if not active_records
                else "Conflicting active participation records were found."
            )
            return NetworkVerificationResult(
                status=NetworkStatus.UNKNOWN,
                member_id=coverage.member.member_id,
                health_plan_id=coverage.health_plan.health_plan_id,
                network_id=coverage.network.network_id,
                provider_id=provider_id,
                provider_location_id=provider_location_id,
                specialty_or_service_code=specialty_or_service_code,
                service_date=service_date,
                source_reference=None,
                reason=reason,
            )

        participation = active_records[0]
        return NetworkVerificationResult(
            status=participation.status,
            member_id=coverage.member.member_id,
            health_plan_id=coverage.health_plan.health_plan_id,
            network_id=coverage.network.network_id,
            provider_id=provider_id,
            provider_location_id=provider_location_id,
            specialty_or_service_code=specialty_or_service_code,
            service_date=service_date,
            source_reference=participation.source_reference,
            reason="Active participation record was found.",
        )
