from pydantic import BaseModel, ConfigDict, Field

from app.application.booking_errors import BookingError
from app.application.service_interfaces import (
    AppointmentBookingService,
    SchedulingWorkflowService,
)
from app.domain.models import ExplicitConfirmation
from app.tools.scheduling_context import (
    SYNTHETIC_CONVERSATION_ID,
    SYNTHETIC_MEMBER_ID,
)


class PrepareBookingConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookConfirmedAppointmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    confirmed: bool


def prepare_booking_confirmation(
    _: PrepareBookingConfirmationRequest,
    booking: AppointmentBookingService,
    scheduling_workflows: SchedulingWorkflowService,
) -> dict:
    """Prepare exact confirmation details without booking."""
    workflow = scheduling_workflows.get_for_conversation(
        SYNTHETIC_MEMBER_ID,
        SYNTHETIC_CONVERSATION_ID,
    )
    if workflow is None:
        return {
            "status": "failed",
            "error_code": "workflow_not_found",
            "message": "A scheduling workflow was not found.",
        }

    try:
        confirmation = booking.prepare_confirmation(
            workflow.workflow_id
        )
    except BookingError as error:
        return _booking_error(error)

    summary = confirmation.summary
    return {
        "confirmation_fingerprint": (
            confirmation.selection_fingerprint
        ),
        "presented_at": confirmation.presented_at.isoformat(),
        "expires_at": confirmation.expires_at.isoformat(),
        "summary": {
            "provider_name": summary.provider_name,
            "specialty": summary.specialty,
            "location": summary.location,
            "start_at": summary.start_at.isoformat(),
            "end_at": summary.end_at.isoformat(),
            "time_zone": summary.time_zone,
            "modality": summary.modality,
            "network_status": summary.network_status.value,
            "limitations": list(summary.limitations),
        },
    }


def book_confirmed_appointment(
    request: BookConfirmedAppointmentRequest,
    booking: AppointmentBookingService,
    scheduling_workflows: SchedulingWorkflowService,
) -> dict:
    """Book only a matching, explicitly confirmed preparation."""
    workflow = scheduling_workflows.get_for_conversation(
        SYNTHETIC_MEMBER_ID,
        SYNTHETIC_CONVERSATION_ID,
    )
    if workflow is None:
        return {
            "status": "failed",
            "error_code": "workflow_not_found",
            "message": "A scheduling workflow was not found.",
        }

    try:
        appointment = booking.book(
            workflow_id=workflow.workflow_id,
            confirmation_fingerprint=(
                request.confirmation_fingerprint
            ),
            explicit_confirmation=ExplicitConfirmation(
                confirmed=request.confirmed
            ),
        )
    except BookingError as error:
        return _booking_error(error)

    return {
        "appointment_id": appointment.appointment_id,
        "status": appointment.status,
        "confirmation_number": appointment.confirmation_number,
    }


def _booking_error(error: BookingError) -> dict:
    return {
        "status": "failed",
        "error_code": error.code,
        "message": str(error),
    }


prepare_booking_confirmation_tool = {
    "type": "function",
    "function": {
        "name": "prepare_booking_confirmation",
        "description": (
            "Prepare the exact selected appointment summary and an "
            "expiring fingerprint. This does not book."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}


book_confirmed_appointment_tool = {
    "type": "function",
    "function": {
        "name": "book_confirmed_appointment",
        "description": (
            "Book the prepared appointment only after the member "
            "explicitly confirms the exact summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "confirmation_fingerprint": {
                    "type": "string",
                    "description": (
                        "Exact fingerprint returned by confirmation "
                        "preparation."
                    ),
                },
                "confirmed": {
                    "type": "boolean",
                    "description": (
                        "True only when the member explicitly confirmed "
                        "the prepared appointment summary."
                    ),
                },
            },
            "required": [
                "confirmation_fingerprint",
                "confirmed",
            ],
            "additionalProperties": False,
        },
    },
}
