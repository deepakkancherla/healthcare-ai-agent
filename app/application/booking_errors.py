class BookingError(RuntimeError):
    code = "booking_error"


class ExplicitConfirmationRequired(BookingError):
    code = "explicit_confirmation_required"


class ConfirmationNotPrepared(BookingError):
    code = "confirmation_not_prepared"


class ConfirmationFingerprintMismatch(BookingError):
    code = "confirmation_fingerprint_mismatch"


class ConfirmationExpired(BookingError):
    code = "confirmation_expired"


class InvalidBookingState(BookingError):
    code = "invalid_booking_state"


class SlotReservationConflict(BookingError):
    code = "slot_unavailable"


class BookingOutcomeUnknown(BookingError):
    code = "booking_outcome_unknown"
