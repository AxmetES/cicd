from datetime import datetime, timedelta

from jose import jwt
from sqlalchemy import select

from app.config import settings
from app.models.models import User


async def test_register_success(async_client, db_session, mock_send_email):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "SecurePass123"},
    )

    assert response.status_code == 200

    result = await db_session.execute(select(User).where(User.email == "newuser@example.com"))
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.is_verified is False
    assert user.verification_token
    mock_send_email.assert_called_once_with("newuser@example.com", user.verification_token)


async def test_register_duplicate_email(async_client):
    payload = {"email": "dup@example.com", "password": "SecurePass123"}

    first = await async_client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = await async_client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


async def test_register_invalid_email(async_client):
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "SecurePass123"},
    )

    assert response.status_code == 422


async def test_verify_email_success(async_client, db_session):
    await async_client.post(
        "/api/auth/register",
        json={"email": "verifyme@example.com", "password": "SecurePass123"},
    )

    result = await db_session.execute(select(User).where(User.email == "verifyme@example.com"))
    user = result.scalar_one()
    token = user.verification_token

    response = await async_client.get(f"/api/auth/verify/{token}")
    assert response.status_code == 200

    await db_session.refresh(user)
    assert user.is_verified is True
    assert user.verification_token is None


async def test_verify_email_invalid_token(async_client):
    response = await async_client.get("/api/auth/verify/does-not-exist")
    assert response.status_code == 400


async def test_verify_email_token_reuse(async_client, db_session):
    await async_client.post(
        "/api/auth/register",
        json={"email": "reuse@example.com", "password": "SecurePass123"},
    )

    result = await db_session.execute(select(User).where(User.email == "reuse@example.com"))
    user = result.scalar_one()
    token = user.verification_token

    first = await async_client.get(f"/api/auth/verify/{token}")
    assert first.status_code == 200

    second = await async_client.get(f"/api/auth/verify/{token}")
    assert second.status_code == 400


async def test_login_success(async_client, verified_user):
    user, password = verified_user

    response = await async_client.post(
        "/api/auth/login", json={"email": user.email, "password": password}
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(async_client, verified_user):
    user, _ = verified_user

    response = await async_client.post(
        "/api/auth/login", json={"email": user.email, "password": "WrongPassword"}
    )

    assert response.status_code == 401


async def test_login_unverified_user(async_client):
    await async_client.post(
        "/api/auth/register",
        json={"email": "unverified@example.com", "password": "SecurePass123"},
    )

    response = await async_client.post(
        "/api/auth/login",
        json={"email": "unverified@example.com", "password": "SecurePass123"},
    )

    assert response.status_code == 403


async def test_login_nonexistent_email(async_client):
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "WhoKnows123"},
    )

    assert response.status_code == 401


async def test_me_with_valid_token(async_client, verified_user, auth_headers):
    user, _ = verified_user

    response = await async_client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["email"] == user.email


async def test_me_without_token(async_client):
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_with_invalid_token(async_client):
    response = await async_client.get(
        "/api/auth/me", headers={"Authorization": "Bearer garbage-token-value"}
    )
    assert response.status_code == 401


async def test_me_with_expired_token(async_client, verified_user):
    user, _ = verified_user

    expired_payload = {
        "sub": str(user.id),
        "exp": datetime.utcnow() - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm="HS256")

    response = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
