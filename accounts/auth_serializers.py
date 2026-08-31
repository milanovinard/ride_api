"""
Serializers for the login / token flow.

`LoginSerializer` is a thin wrapper over SimpleJWT's `TokenObtainPairSerializer`:
authentication (is this an active user with the right password?) is unchanged -
we only enrich the response with the caller's profile so the client gets the
user and the tokens from a single request.

Authorization is deliberately NOT enforced here. Any valid user - admin, rider or
driver - can log in and receive tokens. Whether those tokens may actually call an
endpoint is decided per-request by `accounts.permissions.IsAdminRole`, which reads
the freshly-loaded `user.role`. Keeping the two concerns apart means a demoted
admin's existing token stops working on its next call with no revocation step.
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import UserSerializer


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)  # {"refresh": ..., "access": ...}; sets self.user
        data["user"] = UserSerializer(self.user).data
        return data
