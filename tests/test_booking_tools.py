import pytest
from pydantic import ValidationError

from app.tools.booking import (
    BookConfirmedAppointmentRequest,
    PrepareBookingConfirmationRequest,
    book_confirmed_appointment,
    book_confirmed_appointment_tool,
    prepare_booking_confirmation,
    prepare_booking_confirmation_tool,
)

from .booking_helpers import build_selected_booking_context


def test_prepare_tool_does_not_create_appointment():
    repositories, services, _, _ = (
        build_selected_booking_context()
    )

    result = prepare_booking_confirmation(
        PrepareBookingConfirmationRequest(),
        services.appointment_booking,
        services.scheduling_workflows,
    )

    assert result["summary"]["provider_name"] == (
        "Dr. Sarah Johnson"
    )
    assert result["summary"]["specialty"] == "Dermatology"
    assert result["summary"]["network_status"] == "in_network"
    assert len(result["confirmation_fingerprint"]) == 64
    assert repositories.appointments.list_all() == []


def test_booking_tool_returns_only_service_confirmation():
    repositories, services, _, _ = (
        build_selected_booking_context()
    )
    preparation = prepare_booking_confirmation(
        PrepareBookingConfirmationRequest(),
        services.appointment_booking,
        services.scheduling_workflows,
    )

    result = book_confirmed_appointment(
        BookConfirmedAppointmentRequest(
            confirmation_fingerprint=(
                preparation["confirmation_fingerprint"]
            ),
            confirmed=True,
        ),
        services.appointment_booking,
        services.scheduling_workflows,
    )

    assert set(result) == {
        "appointment_id",
        "status",
        "confirmation_number",
    }
    assert repositories.appointments.get(
        result["appointment_id"]
    ).confirmation_number == result["confirmation_number"]


def test_booking_tool_returns_structured_confirmation_failure():
    _, services, _, _ = build_selected_booking_context()
    preparation = prepare_booking_confirmation(
        PrepareBookingConfirmationRequest(),
        services.appointment_booking,
        services.scheduling_workflows,
    )

    result = book_confirmed_appointment(
        BookConfirmedAppointmentRequest(
            confirmation_fingerprint=(
                preparation["confirmation_fingerprint"]
            ),
            confirmed=False,
        ),
        services.appointment_booking,
        services.scheduling_workflows,
    )

    assert result["status"] == "failed"
    assert result["error_code"] == (
        "explicit_confirmation_required"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "confirmation_fingerprint": "not-a-fingerprint",
            "confirmed": True,
        },
        {
            "confirmation_fingerprint": "0" * 64,
            "confirmed": True,
            "member_id": "someone-else",
        },
        {
            "confirmation_fingerprint": "0" * 64,
            "confirmed": True,
            "confirmation_number": "fabricated",
        },
    ],
)
def test_booking_tool_rejects_invalid_or_authoritative_arguments(
    payload,
):
    with pytest.raises(ValidationError):
        BookConfirmedAppointmentRequest.model_validate(payload)


def test_booking_tool_schemas_exclude_authoritative_outputs():
    prepare_properties = prepare_booking_confirmation_tool[
        "function"
    ]["parameters"]["properties"]
    booking_properties = book_confirmed_appointment_tool[
        "function"
    ]["parameters"]["properties"]

    assert prepare_properties == {}
    assert "member_id" not in booking_properties
    assert "appointment_id" not in booking_properties
    assert "status" not in booking_properties
    assert "confirmation_number" not in booking_properties

    with pytest.raises(ValidationError):
        PrepareBookingConfirmationRequest.model_validate(
            {"member_id": "someone-else"}
        )
