from pydantic import BaseModel


class AppointmentBookingRequest(BaseModel):
    provider_name: str
    patient_name: str
    appointment_date: str
    appointment_time: str


def book_appointment(request: AppointmentBookingRequest):
    """
    Book an appointment with a healthcare provider.

    (Hardcoded implementation for now.)
    """

    return {
        "provider_name": request.provider_name,
        "patient_name": request.patient_name,
        "appointment_date": request.appointment_date,
        "appointment_time": request.appointment_time,
        "confirmation_number": "ABC123",
        "status": "confirmed",
    }


appointment_booking_tool = {
    "type": "function",
    "function": {
        "name": "book_appointment",
        "description": (
            "Book an appointment with a healthcare provider "
            "based on provider name, patient name, date, and time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "provider_name": {
                    "type": "string",
                    "description": "Name of the healthcare provider.",
                },
                "patient_name": {
                    "type": "string",
                    "description": "Name of the patient.",
                },
                "appointment_date": {
                    "type": "string",
                    "description": "Date of the appointment in YYYY-MM-DD format.",
                },
                "appointment_time": {
                    "type": "string",
                    "description": "Time of the appointment in HH:MM format.",
                },
            },
            "required": [
                "provider_name",
                "patient_name",
                "appointment_date",
                "appointment_time",
            ],
        },
    },
}
