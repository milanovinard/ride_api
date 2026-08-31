"""
Login / token endpoints.

These are the only views that opt out of the project-wide `IsAdminRole` default
(see `config/settings.py`):

- `LoginView`   - AllowAny. Credentials-only check; returns `{user, access, refresh}`.
- `RefreshView` - AllowAny. Exchanges a refresh token for a new access token.
- `MeView`      - IsAuthenticated. Any logged-in user may read their own profile.

Every other endpoint keeps the admin-only default, so a non-admin can log in and
hold a valid token but still gets 403 from `/api/rides/`, `/api/users/`, etc.
"""

from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .auth_serializers import LoginSerializer
from .serializers import UserSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class MeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
