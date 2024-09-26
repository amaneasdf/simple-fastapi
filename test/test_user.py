from fastapi import status

from app.main import get_current_user
from app.models import User as UserDB, UserScope as ScopeDB
from app.utils.auth import get_password_hash
from test.utils import client, mock_user_entry


# Overrides
def __override_get_current_user():
    return UserDB(
        id=1,
        username="admin",
        email="admin@localhost.com",
        fullname="Administrator",
        password=get_password_hash("admin"),
        is_active=True,
        role="admin",
        allowed_scopes=[
            ScopeDB(scope="me", is_active=True),
            ScopeDB(scope="admin.assign", is_active=True),
            ScopeDB(scope="users.read", is_active=True),
        ],
    )


def test_unauthorized_read_own_info(client):
    response = client.get("/user/me")

    assert (
        response.status_code == status.HTTP_401_UNAUTHORIZED
    ), "Response code should be 401"
    assert response.json() == {"detail": "Not authenticated"}


def test_read_own_info(client):
    # Setup
    client.app.dependency_overrides[get_current_user] = __override_get_current_user

    # Check
    response = client.get("/user/me")

    assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "email": "admin@localhost.com",
        "fullname": "Administrator",
        "is_active": True,
        "role": "admin",
        "allowed_scopes": [
            {"scope": "me", "is_active": True},
            {"scope": "admin.assign", "is_active": True},
            {"scope": "users.read", "is_active": True},
        ],
    }

    # Teardown
    client.app.dependency_overrides.pop(get_current_user)


def test_read_all_users(client, mock_user_entry):
    # Setup
    client.app.dependency_overrides[get_current_user] = __override_get_current_user

    # Check
    mocked_user = mock_user_entry
    response = client.get("/admin/users/")
    response_json = response.json()

    assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
    assert (
        len(response_json) == 2
    ), "Returned items should be 2 users in total, including initial user"
    assert any(
        user["id"] == 1 and user["role"] == "superadmin" for user in response_json
    ), "Initial user should be present in the list"
    assert any(
        user["id"] == 2 and user["username"] == mocked_user.username
        for user in response_json
    ), "Mocked user should be present in the list"

    # Teardown
    client.app.dependency_overrides.pop(get_current_user)
