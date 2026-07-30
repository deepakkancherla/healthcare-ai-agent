from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.domain.models import (
    Appointment,
    AppointmentSlot,
    Enrollment,
    HealthPlan,
    Member,
    NetworkParticipation,
    NetworkStatus,
    Provider,
    ProviderLocation,
    ProviderNetwork,
)


SYNTHETIC_DATA_VERSION = "v1"
DEFAULT_SERVICE_DATE = date(2026, 8, 4)

MEMBERS = (
    Member(
        member_id="deepak",
        display_name="Deepak",
        status="active",
    ),
    Member(
        member_id="maya",
        display_name="Maya",
        status="active",
    ),
)

ENROLLMENTS = (
    Enrollment(
        enrollment_id="enrollment-deepak-bcbs",
        member_id="deepak",
        health_plan_id="plan-bcbs-ppo",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status="active",
    ),
    Enrollment(
        enrollment_id="enrollment-maya-uhc",
        member_id="maya",
        health_plan_id="plan-uhc-hmo",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status="active",
    ),
)

HEALTH_PLANS = (
    HealthPlan(
        health_plan_id="plan-bcbs-ppo",
        payer_id="BCBS",
        product_name="Blue Choice PPO",
        product_type="PPO",
        network_id="network-bcbs-choice",
    ),
    HealthPlan(
        health_plan_id="plan-uhc-hmo",
        payer_id="UHC",
        product_name="United Select HMO",
        product_type="HMO",
        network_id="network-uhc-select",
    ),
)

NETWORKS = (
    ProviderNetwork(
        network_id="network-bcbs-choice",
        name="BCBS Choice",
        effective_start=date(2025, 1, 1),
        effective_end=date(2027, 12, 31),
    ),
    ProviderNetwork(
        network_id="network-uhc-select",
        name="UHC Select",
        effective_start=date(2025, 1, 1),
        effective_end=date(2027, 12, 31),
    ),
)

PROVIDERS = (
    Provider(
        provider_id="provider-sarah-johnson",
        display_name="Dr. Sarah Johnson",
        specialty_codes=("Dermatology",),
        gender="Female",
        languages=("English",),
        active=True,
    ),
    Provider(
        provider_id="provider-aisha-patel",
        display_name="Dr. Aisha Patel",
        specialty_codes=("Dermatology",),
        gender="Female",
        languages=("English", "Hindi"),
        active=True,
    ),
    Provider(
        provider_id="provider-miguel-rivera",
        display_name="Dr. Miguel Rivera",
        specialty_codes=("Cardiology",),
        gender="Male",
        languages=("English", "Spanish"),
        active=True,
    ),
)

PROVIDER_LOCATIONS = (
    ProviderLocation(
        provider_location_id="location-sarah-plano",
        provider_id="provider-sarah-johnson",
        address="100 Synthetic Health Way",
        city="Plano",
        state="TX",
        postal_code="75024",
        time_zone="America/Chicago",
        modalities=("in_person", "virtual"),
        active=True,
    ),
    ProviderLocation(
        provider_location_id="location-sarah-dallas",
        provider_id="provider-sarah-johnson",
        address="200 Fictional Medical Plaza",
        city="Dallas",
        state="TX",
        postal_code="75201",
        time_zone="America/Chicago",
        modalities=("in_person",),
        active=True,
    ),
    ProviderLocation(
        provider_location_id="location-aisha-frisco",
        provider_id="provider-aisha-patel",
        address="300 Example Care Lane",
        city="Frisco",
        state="TX",
        postal_code="75034",
        time_zone="America/Chicago",
        modalities=("in_person",),
        active=True,
    ),
    ProviderLocation(
        provider_location_id="location-miguel-plano",
        provider_id="provider-miguel-rivera",
        address="400 Sample Cardiology Drive",
        city="Plano",
        state="TX",
        postal_code="75075",
        time_zone="America/Chicago",
        modalities=("in_person",),
        active=True,
    ),
)

NETWORK_PARTICIPATIONS = (
    NetworkParticipation(
        participation_id="participation-bcbs-sarah-plano",
        network_id="network-bcbs-choice",
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        specialty_or_service_code="Dermatology",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status=NetworkStatus.IN_NETWORK,
        source_reference="synthetic:v1:bcbs-sarah-plano",
        verified_at=datetime(
            2026,
            7,
            1,
            12,
            tzinfo=ZoneInfo("UTC"),
        ),
    ),
    NetworkParticipation(
        participation_id="participation-bcbs-sarah-dallas",
        network_id="network-bcbs-choice",
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-dallas",
        specialty_or_service_code="Dermatology",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status=NetworkStatus.OUT_OF_NETWORK,
        source_reference="synthetic:v1:bcbs-sarah-dallas",
        verified_at=datetime(
            2026,
            7,
            1,
            12,
            tzinfo=ZoneInfo("UTC"),
        ),
    ),
    NetworkParticipation(
        participation_id="participation-uhc-sarah-plano",
        network_id="network-uhc-select",
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        specialty_or_service_code="Dermatology",
        effective_start=date(2026, 1, 1),
        effective_end=date(2026, 12, 31),
        status=NetworkStatus.OUT_OF_NETWORK,
        source_reference="synthetic:v1:uhc-sarah-plano",
        verified_at=datetime(
            2026,
            7,
            1,
            12,
            tzinfo=ZoneInfo("UTC"),
        ),
    ),
    NetworkParticipation(
        participation_id="participation-expired-aisha-frisco",
        network_id="network-bcbs-choice",
        provider_id="provider-aisha-patel",
        provider_location_id="location-aisha-frisco",
        specialty_or_service_code="Dermatology",
        effective_start=date(2025, 1, 1),
        effective_end=date(2025, 12, 31),
        status=NetworkStatus.IN_NETWORK,
        source_reference="synthetic:v1:expired-aisha-frisco",
        verified_at=datetime(
            2025,
            12,
            1,
            12,
            tzinfo=ZoneInfo("UTC"),
        ),
    ),
)

SLOTS = (
    AppointmentSlot(
        slot_id="slot-sarah-plano-20260804-1000",
        provider_id="provider-sarah-johnson",
        provider_location_id="location-sarah-plano",
        start_at=datetime(
            2026,
            8,
            4,
            10,
            tzinfo=ZoneInfo("America/Chicago"),
        ),
        end_at=datetime(
            2026,
            8,
            4,
            10,
            30,
            tzinfo=ZoneInfo("America/Chicago"),
        ),
        time_zone="America/Chicago",
        modality="in_person",
        status="available",
        version=1,
    ),
)

APPOINTMENTS: tuple[Appointment, ...] = ()
