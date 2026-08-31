from accounts.models import User


def test_create_user_hashes_password_and_never_returns_it(admin_client):
    response = admin_client.post(
        "/api/users/",
        {"username": "newrider", "role": User.Role.RIDER, "email": "newrider@example.com", "password": "s3cret123"},
        format="json",
    )

    assert response.status_code == 201
    assert "password" not in response.data

    created = User.objects.get(username="newrider")
    assert created.password != "s3cret123"
    assert created.check_password("s3cret123")
