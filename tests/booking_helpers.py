from datetime import datetime, timedelta, timezone

from app.domain.models import AvailabilityQuery, ProviderSearchCriteria
from app.infrastructure.synthetic.composition import (
    build_synthetic_repositories,
    build_synthetic_services,
)
from app.infrastructure.synthetic.fixtures.v1 import (
    DEFAULT_SERVICE_DATE,
)


class MutableClock:
    def __init__(
        self,
        current: datetime = datetime(
            2026,
            8,
            1,
            12,
            tzinfo=timezone.utc,
        ),
    ):
        self.current = current

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


def build_selected_booking_context(
    *,
    slot_id: str = "slot-sarah-plano-20260804-1000",
    clock: MutableClock | None = None,
    confirmation_ttl: timedelta = timedelta(minutes=10),
):
    clock = clock or MutableClock()
    repositories = build_synthetic_repositories()
    services = build_synthetic_services(
        repositories,
        clock=clock,
        confirmation_ttl=confirmation_ttl,
    )

    criteria = ProviderSearchCriteria(
        location="Plano",
        specialty="Dermatology",
        gender="Female",
    )
    candidates = services.provider_directory.search(criteria)
    workflow = services.scheduling_workflows.record_provider_search(
        "deepak",
        "conversation-deepak",
        criteria,
        candidates,
    )
    coverage = services.member_profiles.get_member_context(
        "deepak",
        DEFAULT_SERVICE_DATE,
    )
    candidate = candidates[0]
    network_result = services.network_verification.verify(
        coverage=coverage,
        provider_id=candidate.provider.provider_id,
        provider_location_id=(
            candidate.location.provider_location_id
        ),
        specialty_or_service_code=candidate.matched_specialty,
        service_date=DEFAULT_SERVICE_DATE,
    )
    workflow = (
        services.scheduling_workflows.record_network_verification(
            workflow.workflow_id,
            network_result,
        )
    )

    slot = services.availability.get_current_slot(slot_id)
    query = AvailabilityQuery(
        provider_id=slot.provider_id,
        provider_location_id=slot.provider_location_id,
        start_date=slot.start_at.date(),
        end_date=slot.start_at.date(),
        modality=slot.modality,
    )
    slots = services.availability.search(query)
    workflow = services.scheduling_workflows.record_availability(
        workflow.workflow_id,
        query,
        slots,
    )
    workflow = services.scheduling_workflows.select_slot(
        workflow.workflow_id,
        slot,
    )

    return repositories, services, workflow, clock
