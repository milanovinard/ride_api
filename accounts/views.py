from rest_framework import viewsets

from .models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Full CRUD for users. Access is restricted globally to admin-role
    users via REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES (see config/settings.py)."""

    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
