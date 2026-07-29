from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class NetworkStatus(str, Enum):
    IN_NETWORK = "in_network"
    OUT_OF_NETWORK = "out_of_network"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Member:
    member_id: str
    display_name: str
    status: str


@dataclass(frozen=True)
class Enrollment:
    enrollment_id: str
    member_id: str
    health_plan_id: str
    effective_start: date
    effective_end: date
    status: str

    def is_active_on(self, service_date: date) -> bool:
        return (
            self.status == "active"
            and self.effective_start <= service_date <= self.effective_end
        )


@dataclass(frozen=True)
class HealthPlan:
    health_plan_id: str
    payer_id: str
    product_name: str
    product_type: str
    network_id: str


@dataclass(frozen=True)
class ProviderNetwork:
    network_id: str
    name: str
    effective_start: date
    effective_end: date

    def is_active_on(self, service_date: date) -> bool:
        return self.effective_start <= service_date <= self.effective_end


@dataclass(frozen=True)
class Provider:
    provider_id: str
    display_name: str
    specialty_codes: tuple[str, ...]
    gender: str
    languages: tuple[str, ...]
    active: bool


@dataclass(frozen=True)
class ProviderLocation:
    provider_location_id: str
    provider_id: str
    address: str
    city: str
    state: str
    postal_code: str
    time_zone: str
    modalities: tuple[str, ...]
    active: bool


@dataclass(frozen=True)
class NetworkParticipation:
    participation_id: str
    network_id: str
    provider_id: str
    provider_location_id: str
    specialty_or_service_code: str
    effective_start: date
    effective_end: date
    status: NetworkStatus
    source_reference: str
    verified_at: datetime

    def is_active_on(self, service_date: date) -> bool:
        return self.effective_start <= service_date <= self.effective_end


@dataclass(frozen=True)
class AppointmentSlot:
    slot_id: str
    provider_id: str
    provider_location_id: str
    start_at: datetime
    end_at: datetime
    time_zone: str
    modality: str
    status: str
    version: int


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    member_id: str
    slot_id: str
    status: str
    confirmation_number: str
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True)
class MemberCoverageContext:
    member: Member
    enrollment: Enrollment
    health_plan: HealthPlan
    network: ProviderNetwork


@dataclass(frozen=True)
class ProviderSearchCriteria:
    location: str
    specialty: str
    gender: str | None = None


@dataclass(frozen=True)
class ProviderCandidate:
    provider: Provider
    location: ProviderLocation
    matched_specialty: str


@dataclass(frozen=True)
class NetworkVerificationResult:
    status: NetworkStatus
    member_id: str
    health_plan_id: str
    network_id: str
    provider_id: str
    provider_location_id: str
    specialty_or_service_code: str
    service_date: date
    source_reference: str | None
    reason: str
