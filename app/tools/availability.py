from datetime import date

from pydantic import BaseModel, model_validator

from app.application.service_interfaces import (
    AvailabilityService,
    SchedulingWorkflowService,
)
from app.domain.models import AppointmentSlot, AvailabilityQuery
from app.infrastructure.synthetic.composition import (
    build_synthetic_services,
)
from app.tools.scheduling_context import (
    SYNTHETIC_CONVERSATION_ID,
    SYNTHETIC_MEMBER_ID,
)


class AvailabilitySearchRequest(BaseModel):
    provider_id: str
    provider_location_id: str
    start_date: date
    end_date: date
    modality: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date > self.end_date:
            raise ValueError(
                "Availability start date must not be after end date."
            )
        return self


class AppointmentSelectionRequest(BaseModel):
    slot_id: str


def search_availability(
    request: AvailabilitySearchRequest,
    availability: AvailabilityService | None = None,
    scheduling_workflows: SchedulingWorkflowService | None = None,
) -> dict:
    """Adapt a model request to authoritative slot search."""
    availability_service = (
        availability or build_synthetic_services().availability
    )
    query = AvailabilityQuery(
        provider_id=request.provider_id,
        provider_location_id=request.provider_location_id,
        start_date=request.start_date,
        end_date=request.end_date,
        modality=request.modality,
    )
    slots = availability_service.search(query)

    workflow_id = None
    workflow_state = None
    if scheduling_workflows is not None:
        workflow = scheduling_workflows.start_or_resume(
            member_id=SYNTHETIC_MEMBER_ID,
            conversation_id=SYNTHETIC_CONVERSATION_ID,
        )
        workflow = scheduling_workflows.record_availability(
            workflow_id=workflow.workflow_id,
            query=query,
            slots=slots,
        )
        workflow_id = workflow.workflow_id
        workflow_state = workflow.state.value

    return {
        "slots": [_serialize_slot(slot) for slot in slots],
        "workflow_id": workflow_id,
        "workflow_state": workflow_state,
    }


def select_appointment_slot(
    request: AppointmentSelectionRequest,
    availability: AvailabilityService,
    scheduling_workflows: SchedulingWorkflowService,
) -> dict:
    """Persist an exact slot selection without booking it."""
    workflow = scheduling_workflows.start_or_resume(
        member_id=SYNTHETIC_MEMBER_ID,
        conversation_id=SYNTHETIC_CONVERSATION_ID,
    )
    slot = availability.get_current_slot(request.slot_id)
    workflow = scheduling_workflows.select_slot(
        workflow_id=workflow.workflow_id,
        slot=slot,
    )
    selection = workflow.selection
    if selection is None:
        raise RuntimeError("The workflow did not persist a selection.")

    return {
        "workflow_id": workflow.workflow_id,
        "workflow_state": workflow.state.value,
        "requires_confirmation": True,
        "selection": {
            "slot_id": selection.slot_id,
            "slot_version": selection.slot_version,
            "provider_id": selection.provider_id,
            "provider_location_id": selection.provider_location_id,
            "start_at": selection.start_at.isoformat(),
            "end_at": selection.end_at.isoformat(),
            "time_zone": selection.time_zone,
            "modality": selection.modality,
            "network_status": selection.network_status.value,
            "health_plan_id": selection.health_plan_id,
            "network_id": selection.network_id,
            "network_source_reference": (
                selection.network_source_reference
            ),
            "network_service_date": (
                selection.network_service_date.isoformat()
            ),
        },
    }


def _serialize_slot(slot: AppointmentSlot) -> dict:
    return {
        "slot_id": slot.slot_id,
        "provider_id": slot.provider_id,
        "provider_location_id": slot.provider_location_id,
        "start_at": slot.start_at.isoformat(),
        "end_at": slot.end_at.isoformat(),
        "time_zone": slot.time_zone,
        "modality": slot.modality,
        "status": slot.status,
        "version": slot.version,
    }


availability_search_tool = {
    "type": "function",
    "function": {
        "name": "search_availability",
        "description": (
            "Search authoritative appointment slots for a verified "
            "provider and location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "provider_id": {
                    "type": "string",
                    "description": "Stable provider identifier.",
                },
                "provider_location_id": {
                    "type": "string",
                    "description": "Stable provider-location identifier.",
                },
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "First acceptable appointment date.",
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Last acceptable appointment date.",
                },
                "modality": {
                    "type": "string",
                    "description": "Optional in_person or virtual filter.",
                },
            },
            "required": [
                "provider_id",
                "provider_location_id",
                "start_date",
                "end_date",
            ],
        },
    },
}


appointment_selection_tool = {
    "type": "function",
    "function": {
        "name": "select_appointment_slot",
        "description": (
            "Select one exact slot and prepare its details for member "
            "confirmation. This does not book the appointment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {
                    "type": "string",
                    "description": (
                        "Stable identifier of a previously presented slot."
                    ),
                },
            },
            "required": ["slot_id"],
        },
    },
}
