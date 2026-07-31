from datetime import date

import pytest

from app.application.services import MemberContextError
from app.domain.models import (
    NetworkStatus,
    ProviderSearchCriteria,
)
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.infrastructure.synthetic.fixtures.v1 import (
    DEFAULT_SERVICE_DATE,
)


@pytest.fixture
def services():
    return build_synthetic_services()


def test_provider_search_applies_specialty_location_and_gender(
    services,
):
    matches = services.provider_directory.search(
        ProviderSearchCriteria(
            specialty="dermatology",
            location="plano",
            gender="female",
        )
    )

    assert len(matches) == 1
    assert matches[0].provider.display_name == "Dr. Sarah Johnson"
    assert matches[0].location.city == "Plano"
    assert matches[0].matched_specialty == "Dermatology"


def test_provider_search_returns_no_match_for_a_hard_constraint(
    services,
):
    matches = services.provider_directory.search(
        ProviderSearchCriteria(
            specialty="Cardiology",
            location="Plano",
            gender="Female",
        )
    )

    assert matches == []


def test_member_context_uses_active_enrollment_plan_and_network(
    services,
):
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )

    assert coverage.health_plan.health_plan_id == "plan-bcbs-ppo"
    assert coverage.network.network_id == "network-bcbs-choice"


def test_member_context_fails_when_no_active_enrollment_exists(
    services,
):
    with pytest.raises(
        MemberContextError,
        match="Exactly one active enrollment",
    ):
        services.member_profiles.get_member_context(
            "deepak",
            date(2027, 1, 1),
        )


def test_network_verification_is_specific_to_member_plan(services):
    provider = services.provider_directory.resolve(
        "Dr. Sarah Johnson",
        provider_location="Plano",
        specialty="Dermatology",
    )
    assert provider is not None

    deepak_coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    maya_coverage = services.member_profiles.get_member_context(
        "maya",
        DEFAULT_SERVICE_DATE,
    )

    deepak_result = services.network_verification.verify(
        coverage=deepak_coverage,
        provider_id=provider.provider.provider_id,
        provider_location_id=(
            provider.location.provider_location_id
        ),
        specialty_or_service_code=provider.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )
    maya_result = services.network_verification.verify(
        coverage=maya_coverage,
        provider_id=provider.provider.provider_id,
        provider_location_id=(
            provider.location.provider_location_id
        ),
        specialty_or_service_code=provider.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )

    assert deepak_result.status == NetworkStatus.IN_NETWORK
    assert maya_result.status == NetworkStatus.OUT_OF_NETWORK
    assert deepak_result.network_id != maya_result.network_id


def test_network_verification_is_specific_to_provider_location(
    services,
):
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    plano = services.provider_directory.resolve(
        "Dr. Sarah Johnson",
        provider_location="Plano",
        specialty="Dermatology",
    )
    dallas = services.provider_directory.resolve(
        "Dr. Sarah Johnson",
        provider_location="Dallas",
        specialty="Dermatology",
    )
    assert plano is not None
    assert dallas is not None

    plano_result = services.network_verification.verify(
        coverage=coverage,
        provider_id=plano.provider.provider_id,
        provider_location_id=plano.location.provider_location_id,
        specialty_or_service_code=plano.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )
    dallas_result = services.network_verification.verify(
        coverage=coverage,
        provider_id=dallas.provider.provider_id,
        provider_location_id=dallas.location.provider_location_id,
        specialty_or_service_code=dallas.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )

    assert plano_result.status == NetworkStatus.IN_NETWORK
    assert dallas_result.status == NetworkStatus.OUT_OF_NETWORK


def test_expired_participation_fails_closed_as_unknown(services):
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    provider = services.provider_directory.resolve(
        "Dr. Aisha Patel",
        provider_location="Frisco",
        specialty="Dermatology",
    )
    assert provider is not None

    result = services.network_verification.verify(
        coverage=coverage,
        provider_id=provider.provider.provider_id,
        provider_location_id=(
            provider.location.provider_location_id
        ),
        specialty_or_service_code=provider.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )

    assert result.status == NetworkStatus.UNKNOWN
    assert result.source_reference is None
    assert result.reason == (
        "No active participation record was found."
    )


def test_missing_specialty_participation_fails_closed_as_unknown(
    services,
):
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )

    result = services.network_verification.verify(
        coverage=coverage,
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        specialty_or_service_code="Cardiology",
        service_date=DEFAULT_SERVICE_DATE,
    )

    assert result.status == NetworkStatus.UNKNOWN


def test_network_verification_requires_coverage_on_service_date(
    services,
):
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )

    result = services.network_verification.verify(
        coverage=coverage,
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        specialty_or_service_code="Dermatology",
        service_date=date(2027, 1, 1),
    )

    assert result.status == NetworkStatus.UNKNOWN
    assert result.reason == (
        "Member coverage is not active on the service date."
    )
