import pytest
from rest_framework.test import APIClient

USERS_URL = "/api/users/"


def test_anonymous_request_is_rejected():
    response = APIClient().get(USERS_URL)
    assert response.status_code == 401


def test_non_admin_role_is_forbidden(rider_client):
    response = rider_client.get(USERS_URL)
    assert response.status_code == 403


def test_admin_role_is_allowed(admin_client):
    response = admin_client.get(USERS_URL)
    assert response.status_code == 200
