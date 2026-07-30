from datetime import date
from typing import Protocol

from app.domain.models import (
    MemberCoverageContext,
    NetworkVerificationResult,
    ProviderCandidate,
    ProviderSearchCriteria,
)


class MemberProfileService(Protocol):
    def get_member_context(
        self,
        member_id: str,
        service_date: date,
    ) -> MemberCoverageContext: ...


class ProviderDirectoryService(Protocol):
    def search(
        self,
        criteria: ProviderSearchCriteria,
    ) -> list[ProviderCandidate]: ...

    def resolve(
        self,
        provider_name: str,
        provider_location: str | None = None,
        specialty: str | None = None,
    ) -> ProviderCandidate | None: ...


class NetworkVerificationService(Protocol):
    def verify(
        self,
        coverage: MemberCoverageContext,
        provider_id: str,
        provider_location_id: str,
        specialty_or_service_code: str,
        service_date: date,
    ) -> NetworkVerificationResult: ...
