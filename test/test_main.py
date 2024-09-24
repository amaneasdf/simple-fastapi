import base64
from datetime import timedelta
from fastapi import status

from app.main import SETTINGS, get_db
from app.models import User as UserDB
from .utils import TestingSessionLocal, client, override_get_db


def test_ensure_initial_admin_user_is_created(client):
    # Ensure that initial admin user is created
    db = TestingSessionLocal()
    user = db.query(UserDB).filter(UserDB.role == "superadmin").first()

    db.close()

    assert user, "Admin user should be created"


def test_read_root(client):
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
    assert response.json() == {"status": "ok"}, 'Body should be {"status": "ok"}'


def test_health_check(client):
    response = client.get("/health")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
    assert data["time"] is not None, "Time should be set"
    assert data == {
        "status": "healthy",
        "time": data["time"],
        "db": {
            "alias": "localdb",
            "status": "healthy",
        },
    }, "Data should be healthy"


def test_health_check_db_down(client):
    # Setup
    def __override_get_db():
        session = TestingSessionLocal()
        session.bind = lambda: None

        return session

    client.app.dependency_overrides[get_db] = __override_get_db

    # Check
    response = client.get("/health")
    data = response.json()

    assert (
        response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    ), "Response code should be 503"
    assert (
        data["detail"] == "Database is not available"
    ), "Detail should be 'Database is not available'"

    # Teardown
    client.app.dependency_overrides[get_db] = override_get_db


def test_token_auth(client):
    basic = "Basic " + base64.b64encode(
        ":".join(
            [
                SETTINGS.first_admin_username,
                SETTINGS.first_admin_password.get_secret_value(),
            ]
        ).encode("ascii")
    ).decode("ascii")
    response = client.post("/token", headers={"Authorization": basic})
    expires = timedelta(minutes=SETTINGS.access_token_expire_minutes).total_seconds()

    assert response.status_code == status.HTTP_200_OK, "Response code should be 200"
    assert "access_token" in response.json(), "Token should be in the response"
    assert "token_type" in response.json(), "Token type should be in the response"
    assert "expires_in" in response.json(), "Expires in should be in the response"
    assert (
        response.json()["expires_in"] == expires
    ), "Expires in should be same as the settings"


def test_token_auth_invalid_creds(client):
    basic = "Basic " + base64.b64encode(
        ":".join(
            [
                "invalid",
                "invalid",
            ]
        ).encode("ascii")
    ).decode("ascii")
    response = client.post("/token", headers={"Authorization": basic})

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), "Response code should be 400"
    assert "detail" in response.json(), "Detail should be in the response"
    assert response.json()["detail"] == "Not authenticated"


def test_token_auth_missing_creds(client):
    response = client.post("/token")

    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
    ), "Response code should be 400"
    assert (
        "WWW-Authenticate" in response.headers
    ), "WWW-Authenticate should be in the headers"
    assert (
        response.headers.get("WWW-Authenticate") == "Basic"
    ), "WWW-Authenticate value should be 'Basic'"
