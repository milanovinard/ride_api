"""
Login flow: every valid user can authenticate and receive tokens, but only an
admin-role token may call the business endpoints.
"""

from rest_framework.test import APIClient

LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
ME_URL = "/api/auth/me/"
RIDES_URL = "/api/rides/"

PASSWORD = "pw"  # matches the fixtures in conftest.py


def _login(username):
    return APIClient().post(
        LOGIN_URL, {"username": username, "password": PASSWORD}, format="json"
    )


def test_any_valid_user_can_log_in_and_receives_tokens(rider_user):
    response = _login("rider")

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["user"]["role"] == "rider"
    assert "password" not in response.data["user"]


def test_login_rejects_wrong_password(rider_user):
    response = APIClient().post(
        LOGIN_URL, {"username": "rider", "password": "nope"}, format="json"
    )

    assert response.status_code == 401


def test_non_admin_token_is_forbidden_from_the_api(rider_user):
    access = _login("rider").data["access"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert client.get(RIDES_URL).status_code == 403


def test_admin_token_can_call_the_api(admin_user):
    access = _login("admin").data["access"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert client.get(RIDES_URL).status_code == 200


def test_refresh_returns_a_new_access_token(rider_user):
    refresh = _login("rider").data["refresh"]

    response = APIClient().post(REFRESH_URL, {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert "access" in response.data


def test_me_returns_the_authenticated_user(rider_user):
    access = _login("rider").data["access"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get(ME_URL)

    assert response.status_code == 200
    assert response.data["username"] == "rider"
    assert response.data["role"] == "rider"


def test_me_requires_authentication():
    assert APIClient().get(ME_URL).status_code == 401
