import pytest
from pydantic import ValidationError

from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.tools.insurance import (
    InsuranceVerificationRequest,
    insurance_verification_tool,
    verify_insurance,
)
from app.tools.provider_search import (
    ProviderSearchRequest,
    provider_search,
)


@pytest.fixture
def services():
    return build_synthetic_services()


def test_provider_tool_returns_structured_service_results(services):
    result = provider_search(
        ProviderSearchRequest(
            location="Plano",
            specialty="Dermatology",
            gender="Female",
        ),
        services.provider_directory,
    )

    assert result == [
        {
            "provider_id": "provider-sarah-johnson",
            "provider_location_id": "location-sarah-plano",
            "name": "Dr. Sarah Johnson",
            "specialty": "Dermatology",
            "location": "Plano",
            "address": "100 Synthetic Health Way",
            "gender": "Female",
            "languages": ["English"],
            "modalities": ["in_person", "virtual"],
        }
    ]


def test_provider_tool_retains_direct_call_compatibility():
    result = provider_search(
        ProviderSearchRequest(
            location="Plano",
            specialty="Dermatology",
        )
    )

    assert result[0]["provider_id"] == "provider-sarah-johnson"


def test_insurance_tool_preserves_legacy_contract_and_adds_status(
    services,
):
    result = verify_insurance(
        InsuranceVerificationRequest(
            insurance_name="BCBS",
            provider_name="Dr. Sarah Johnson",
        ),
        services.member_profiles,
        services.provider_directory,
        services.network_verification,
    )

    assert result["accepted"] is True
    assert result["network_status"] == "in_network"
    assert result["health_plan_id"] == "plan-bcbs-ppo"
    assert result["provider_location_id"] == "location-sarah-plano"
    assert result["source_reference"] == (
        "synthetic:v1:bcbs-sarah-plano"
    )


def test_insurance_tool_retains_direct_call_compatibility():
    result = verify_insurance(
        InsuranceVerificationRequest(
            insurance_name="BCBS",
            provider_name="Dr. Sarah Johnson",
        )
    )

    assert result["network_status"] == "in_network"


def test_insurance_tool_returns_location_specific_status(services):
    result = verify_insurance(
        InsuranceVerificationRequest(
            insurance_name="BCBS",
            provider_name="Dr. Sarah Johnson",
            provider_location="Dallas",
            specialty="Dermatology",
            service_date="2026-08-04",
        ),
        services.member_profiles,
        services.provider_directory,
        services.network_verification,
    )

    assert result["accepted"] is False
    assert result["network_status"] == "out_of_network"
    assert result["provider_location_id"] == "location-sarah-dallas"


def test_insurance_tool_returns_unknown_for_unmatched_plan(services):
    result = verify_insurance(
        InsuranceVerificationRequest(
            insurance_name="UHC",
            provider_name="Dr. Sarah Johnson",
        ),
        services.member_profiles,
        services.provider_directory,
        services.network_verification,
    )

    assert result["accepted"] is False
    assert result["network_status"] == "unknown"
    assert "does not match" in result["reason"]


def test_insurance_tool_validates_service_date():
    with pytest.raises(ValidationError):
        InsuranceVerificationRequest(
            insurance_name="BCBS",
            provider_name="Dr. Sarah Johnson",
            service_date="not-a-date",
        )


def test_insurance_tool_advertises_network_verification_dimensions():
    properties = insurance_verification_tool["function"]["parameters"][
        "properties"
    ]

    assert {
        "provider_location",
        "specialty",
        "service_date",
    } <= properties.keys()
