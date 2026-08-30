from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import get_db
from app.main import app
from app.models.models import Base, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(db_session_factory):
    async with db_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def mock_send_email():
    with pytest.MonkeyPatch.context() as mp:
        mock = MagicMock()
        mp.setattr("app.api.endpoints.auth.send_verification_email", mock)
        yield mock


@pytest_asyncio.fixture
async def async_client(db_session_factory):
    async def override_get_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def verified_user(db_session):
    password = "TestPassword123!"
    user = User(
        email="verified@example.com",
        password_hash=hash_password(password),
        is_verified=True,
        verification_token=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password


@pytest_asyncio.fixture
async def auth_headers(async_client, verified_user):
    user, password = verified_user
    response = await async_client.post(
        "/api/auth/login", json={"email": user.email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def make_verified_user(db_session, async_client):
    async def _make(email: str, password: str = "TestPassword123!"):
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_verified=True,
            verification_token=None,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await async_client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return user, headers

    return _make
