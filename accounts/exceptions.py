from common.exceptions import PermissionDeniedError, ResourceNotFoundError


class UserNotFoundError(ResourceNotFoundError):
    default_detail = "User not found."
    default_code = "user_not_found"


class AdminOnlyActionError(PermissionDeniedError):
    default_detail = "This action is restricted to admin users."
    default_code = "admin_only_action"
