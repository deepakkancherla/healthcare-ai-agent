from datetime import date

from app.domain.models import Enrollment, NetworkStatus
from app.infrastructure.synthetic.fixtures.v1 import (
    NETWORK_PARTICIPATIONS,
    SYNTHETIC_DATA_VERSION,
)


def test_synthetic_fixture_version_is_explicit():
    assert SYNTHETIC_DATA_VERSION == "v1"


def test_enrollment_effective_dates_are_inclusive():
    enrollment = Enrollment(
        enrollment_id="enrollment-test",
        member_id="member-test",
        health_plan_id="plan-test",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status="active",
    )

    assert enrollment.is_active_on(date(2026, 1, 1))
    assert enrollment.is_active_on(date(2026, 12, 31))
    assert not enrollment.is_active_on(date(2027, 1, 1))


def test_network_participation_has_structured_status_and_provenance():
    participation = NETWORK_PARTICIPATIONS[0]

    assert participation.status == NetworkStatus.IN_NETWORK
    assert participation.source_reference.startswith("synthetic:v1:")
    assert participation.verified_at.tzinfo is not None
