from common.exceptions import ConflictError, ResourceNotFoundError


class RideNotFoundError(ResourceNotFoundError):
    default_detail = "Ride not found."
    default_code = "ride_not_found"


class InvalidRideStatusTransitionError(ConflictError):
    default_detail = "This ride status transition is not allowed."
    default_code = "invalid_ride_status_transition"


class DriverNotAssignedError(ConflictError):
    default_detail = "This ride does not have a driver assigned."
    default_code = "driver_not_assigned"
