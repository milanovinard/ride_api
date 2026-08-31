"""
Access control for the API: every endpoint is admin-only per the spec.
"""

from rest_framework.permissions import BasePermission

from .models import User


class IsAdminRole(BasePermission):
    """Grants access only to authenticated users whose role is 'admin'.

    Distinct from DRF's own concept of an "admin" (is_staff/is_superuser):
    this checks the domain `User.role` field the spec defines.
    """

    message = "Only users with the 'admin' role may access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)
