import pytest
from rest_framework.test import APIClient

from accounts.models import User


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
    return user


@pytest.fixture
def rider_user(db):
    user = User.objects.create_user(
        username="rider", password="pw", role=User.Role.RIDER, email="rider@example.com"
    )
    return user


@pytest.fixture
def driver_user(db):
    user = User.objects.create_user(
        username="driver", password="pw", role=User.Role.DRIVER, email="driver@example.com"
    )
    return user


def _authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    return _authed_client(admin_user)


@pytest.fixture
def rider_client(rider_user):
    return _authed_client(rider_user)
