"""
Base application exceptions, shared across all apps.

Subclassing DRF's APIException means each of these already renders as a
proper JSON error response with the right HTTP status code, with no extra
view or handler code required. App-specific exceptions (see
accounts/exceptions.py, rides/exceptions.py) should subclass one of these
rather than APIException directly, so every domain error carries a
consistent status_code/default_code shape.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class ApplicationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An application error occurred."
    default_code = "application_error"


class ResourceNotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ConflictError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


class PermissionDeniedError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"
