from datetime import datetime, timezone
import pytest
from fastapi import status
from sqlalchemy import null

from app.main import get_current_user
from app.models import (
    AccessToken as AccessTokenDB,
    User as UserDB,
    UserScope as ScopeDB,
)
from app.utils.auth import verify_password
from test.utils import USER_DATA, TestingSessionLocal, client, mock_user_entry


@pytest.mark.usefixtures("client")
class TestUserUnauthorized:
    """
    Tests user related features when user is not authenticated.
    """

    def test_unauthorized_read_own_info(self, client):
        response = client.get("/profile")

        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), "Response code should be 401"
        assert response.json() == {"detail": "Not authenticated"}

    def test_unauthorized_update_own_info(self, client):
        response = client.patch("/profile")

        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), "Response code should be 401"
        assert response.json() == {"detail": "Not authenticated"}

    def test_unauthorized_change_own_password(self, client):
        response = client.patch("/profile/change-password")

        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), "Response code should be 401"
        assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.usefixtures("client", "mock_user_entry")
class TestUserAuthorized:
    """
    Tests user related features when user is authenticated.
    """

    # Overrides
    @staticmethod
    def override_get_current_user() -> UserDB:
        """
        Overrides the dependency get_current_user with a mock user
        to represent the authenticated user.

        Returns:
            UserDB: A mock user
        """
        return UserDB(
            **{
                **USER_DATA,
                "id": 2,
                "allowed_scopes": [
                    ScopeDB(**scope) for scope in USER_DATA["allowed_scopes"]
                ],
            }
        )

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def class_fixture(cls, client):
        """
        Setup:
            - Override get_current_user with a mock user

        Teardown:
            - Restore original get_current_user
        """
        client.app.dependency_overrides[get_current_user] = (
            cls.override_get_current_user
        )

        yield

        client.app.dependency_overrides.pop(get_current_user)

    @pytest.fixture(scope="function")
    def mock_token_entry(cls):
        with TestingSessionLocal() as db:
            # Setup
            token = AccessTokenDB(
                token="token",
                user_id=2,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                expired_at=int(datetime.now(timezone.utc).timestamp()) + 3600,
            )
            db.add(token)
            db.commit()
            db.refresh(token)

            yield token

            # Teardown
            db.delete(token)
            db.commit()

    # Tests
    def test_authorized_read_own_info(self, client):
        """
        Scenario:
            - Get user information using /profile endpoint

        Expected:
            - Correct response code
            - Correct response payload with expected fields and values
        """
        # Setup
        expected_user = {**USER_DATA, "id": 2}
        del expected_user["password"]

        # Check
        response = client.get("/profile")

        assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
        assert response.json() == expected_user, "Returned user should match expected"

    def test_update_own_info_invalid_email(self, client):
        """
        Scenario:
            - Try to update own information with invalid email

        Expected:
            - Response code 422
        """
        response = client.patch("/profile", json={"email": "invalid_email"})

        assert (
            response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        ), "Response code should be 422"

    def test_update_own_info_no_input(self, client):
        """
        Scenario:
            - Try to update own information with no input

        Expected:
            - Response code 422
        """
        response = client.patch("/profile", json={})

        assert (
            response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        ), "Response code should be 422"

    def test_update_own_info_empty_input(self, client):
        """
        Scenario:
            - Try to update own information with null or empty input

        Expected:
            - Response code 400
        """
        response = client.patch("/profile", json={"email": None, "fullname": ""})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), "Response code should be 400"
        assert response.json() == {"detail": "No fields to update"}

    def test_update_own_info(self, client):
        """
        Scenario:
            - Update own information using /profile endpoint

        Expected:
            - Response code 200
            - Correct response payload with expected fields and values
            - User should be updated in the database
        """
        # Setup
        expected_user = {**USER_DATA, "id": 2}
        expected_user["email"] = "new_email@fake.com"
        expected_user["fullname"] = "new fullname"
        del expected_user["password"]
        del expected_user["allowed_scopes"]

        # Check
        response = client.patch(
            "/profile",
            json={
                "email": expected_user["email"],
                "fullname": expected_user["fullname"],
            },
        )
        response_user = response.json()
        del response_user["allowed_scopes"]

        assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
        assert response_user == expected_user, "Returned user should match expected"

        # Check
        with TestingSessionLocal() as db:
            user = db.query(UserDB).filter(UserDB.id == 2).first()
            assert user.email == expected_user["email"]
            assert user.fullname == expected_user["fullname"]

    def test_change_own_password_wrong_password(self, client):
        """
        Scenario:
            - Try to change own password using wrong old password

        Expected:
            - Response code 400
            - Response body {"detail": "Cannot change password"}
        """
        # Check
        response = client.patch(
            "/profile/change-password",
            json={"old_password": "wrong_password", "new_password": "NewPassword123!"},
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), "Response code should be 400"
        assert response.json() == {"detail": "Cannot change password"}

    def test_change_own_password_new_password_invalid(self, client):
        """
        Scenario:
            - Try to change own password with invalid new password

        Expected:
            - Response code 422
        """
        response = client.patch(
            "/profile/change-password",
            json={"old_password": "admin", "new_password": "123"},
        )

        assert (
            response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        ), "Response code should be 422"

    def test_change_own_password(self, client, mock_user_entry, mock_token_entry):
        """
        Scenario:
            - Change own password

        Expected:
            - Response code 204
            - Response body must be empty
            - Password should be changed in the database
            - Active access tokens should be revoked
        """
        # Mock
        new_password = "NewPassword123!"

        # Check
        response = client.patch(
            "/profile/change-password",
            json={"old_password": "admin", "new_password": new_password},
        )
        assert (
            response.status_code == status.HTTP_204_NO_CONTENT
        ), "Response code should be 204"
        assert response.text == "", "Response should be empty"

        # Check
        with TestingSessionLocal() as db:
            user = db.query(UserDB).filter(UserDB.id == mock_user_entry.id).first()
            assert verify_password(
                new_password, user.password
            ), "Password should be changed"

            existing_token = (
                db.query(AccessTokenDB)
                .filter(AccessTokenDB.id == mock_token_entry.id)
                .first()
            )
            assert existing_token.is_revoked, "Access token should be revoked"

    def test_read_all_users(self, client, mock_user_entry):
        """
        Scenario:
            - Get all registered users using /admin/users/ endpoint

        Expected:
            - Response code 200
            - Response body must contain 2 users
            - Initial user should be present
            - Mocked user should be present
        """
        # Check
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
            user["id"] == 2 and user["username"] == mock_user_entry.username
            for user in response_json
        ), "Mocked user should be present in the list"
