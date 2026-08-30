from io import BytesIO
from unittest.mock import patch

from sqlalchemy import select

from app.models.models import Resume


def _resume_payload(slug="john-doe", **overrides):
    payload = {
        "slug": slug,
        "full_name": "John Doe",
        "role": "Backend Developer",
        "description": "Experienced backend developer",
        "location": "Remote",
        "photo_url": None,
    }
    payload.update(overrides)
    return payload


def _experience_payload(**overrides):
    payload = {
        "role": "Engineer",
        "company": "Acme",
        "period": "2020-2022",
        "description": "Built things",
    }
    payload.update(overrides)
    return payload


def _education_payload(**overrides):
    payload = {
        "title": "BSc Computer Science",
        "place": "State University",
        "period": "2016-2020",
        "description": "Studied CS",
    }
    payload.update(overrides)
    return payload


def _project_payload(**overrides):
    payload = {
        "name": "Cool Project",
        "url": "https://example.com",
        "description": "A cool project",
    }
    payload.update(overrides)
    return payload


# ---- resume ----


async def test_get_my_resume_not_found(async_client, auth_headers):
    response = await async_client.get("/api/resume/me", headers=auth_headers)
    assert response.status_code == 404


async def test_create_resume_via_put(async_client, auth_headers, verified_user):
    user, _ = verified_user

    response = await async_client.put(
        "/api/resume/me", json=_resume_payload(), headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "john-doe"
    assert body["full_name"] == "John Doe"
    assert body["user_id"] == user.id
    assert body["experience"] == []
    assert body["education"] == []
    assert body["projects"] == []


async def test_update_resume_via_put(async_client, auth_headers, db_session, verified_user):
    user, _ = verified_user

    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)
    response = await async_client.put(
        "/api/resume/me",
        json=_resume_payload(full_name="John Updated", location="NYC"),
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "John Updated"
    assert body["location"] == "NYC"

    result = await db_session.execute(select(Resume).where(Resume.user_id == user.id))
    resumes = result.scalars().all()
    assert len(resumes) == 1


async def test_create_resume_duplicate_slug(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="taken-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("other@example.com")
    response = await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="taken-slug"), headers=other_headers
    )

    assert response.status_code in (400, 409)


async def test_resume_requires_auth(async_client):
    get_response = await async_client.get("/api/resume/me")
    assert get_response.status_code == 401

    put_response = await async_client.put("/api/resume/me", json=_resume_payload())
    assert put_response.status_code == 401


# ---- experience ----


async def test_add_experience(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)

    response = await async_client.post(
        "/api/resume/me/experience", json=_experience_payload(), headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Acme"

    resume = (await async_client.get("/api/resume/me", headers=auth_headers)).json()
    assert len(resume["experience"]) == 1
    assert resume["experience"][0]["id"] == body["id"]


async def test_add_experience_without_resume(async_client, auth_headers):
    response = await async_client.post(
        "/api/resume/me/experience", json=_experience_payload(), headers=auth_headers
    )
    assert response.status_code == 404


async def test_update_experience(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)
    created = (
        await async_client.post(
            "/api/resume/me/experience", json=_experience_payload(), headers=auth_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/experience/{created['id']}",
        json=_experience_payload(company="NewCo"),
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["company"] == "NewCo"


async def test_update_experience_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("owner2@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="other-slug"), headers=other_headers
    )
    other_experience = (
        await async_client.post(
            "/api/resume/me/experience", json=_experience_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/experience/{other_experience['id']}",
        json=_experience_payload(company="Hijacked"),
        headers=auth_headers,
    )

    assert response.status_code in (403, 404)


async def test_delete_experience(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)
    created = (
        await async_client.post(
            "/api/resume/me/experience", json=_experience_payload(), headers=auth_headers
        )
    ).json()

    response = await async_client.delete(
        f"/api/resume/me/experience/{created['id']}", headers=auth_headers
    )
    assert response.status_code == 200

    resume = (await async_client.get("/api/resume/me", headers=auth_headers)).json()
    assert resume["experience"] == []


async def test_delete_experience_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("owner3@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="other-slug-2"), headers=other_headers
    )
    other_experience = (
        await async_client.post(
            "/api/resume/me/experience", json=_experience_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.delete(
        f"/api/resume/me/experience/{other_experience['id']}", headers=auth_headers
    )

    assert response.status_code in (403, 404)


# ---- education ----


async def test_add_education(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)

    response = await async_client.post(
        "/api/resume/me/education", json=_education_payload(), headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["place"] == "State University"


async def test_add_education_without_resume(async_client, auth_headers):
    response = await async_client.post(
        "/api/resume/me/education", json=_education_payload(), headers=auth_headers
    )
    assert response.status_code == 404


async def test_update_education(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)
    created = (
        await async_client.post(
            "/api/resume/me/education", json=_education_payload(), headers=auth_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/education/{created['id']}",
        json=_education_payload(place="New University"),
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["place"] == "New University"


async def test_update_education_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("edu2@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="edu-other-slug"), headers=other_headers
    )
    other_education = (
        await async_client.post(
            "/api/resume/me/education", json=_education_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/education/{other_education['id']}",
        json=_education_payload(place="Hijacked University"),
        headers=auth_headers,
    )

    assert response.status_code in (403, 404)


async def test_delete_education_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("edu3@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="edu-other-slug-2"), headers=other_headers
    )
    other_education = (
        await async_client.post(
            "/api/resume/me/education", json=_education_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.delete(
        f"/api/resume/me/education/{other_education['id']}", headers=auth_headers
    )

    assert response.status_code in (403, 404)


# ---- projects ----


async def test_add_project(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)

    response = await async_client.post(
        "/api/resume/me/projects", json=_project_payload(), headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Cool Project"


async def test_add_project_without_resume(async_client, auth_headers):
    response = await async_client.post(
        "/api/resume/me/projects", json=_project_payload(), headers=auth_headers
    )
    assert response.status_code == 404


async def test_update_project(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(), headers=auth_headers)
    created = (
        await async_client.post(
            "/api/resume/me/projects", json=_project_payload(), headers=auth_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/projects/{created['id']}",
        json=_project_payload(name="Renamed Project"),
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Project"


async def test_update_project_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("proj2@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="proj-other-slug"), headers=other_headers
    )
    other_project = (
        await async_client.post(
            "/api/resume/me/projects", json=_project_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.put(
        f"/api/resume/me/projects/{other_project['id']}",
        json=_project_payload(name="Hijacked"),
        headers=auth_headers,
    )

    assert response.status_code in (403, 404)


async def test_delete_project_not_owned(async_client, auth_headers, make_verified_user):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="owner-slug"), headers=auth_headers)

    _, other_headers = await make_verified_user("proj3@example.com")
    await async_client.put(
        "/api/resume/me", json=_resume_payload(slug="proj-other-slug-2"), headers=other_headers
    )
    other_project = (
        await async_client.post(
            "/api/resume/me/projects", json=_project_payload(), headers=other_headers
        )
    ).json()

    response = await async_client.delete(
        f"/api/resume/me/projects/{other_project['id']}", headers=auth_headers
    )

    assert response.status_code in (403, 404)


# ---- public resume ----


async def test_public_resume_by_slug(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="public-slug"), headers=auth_headers)
    await async_client.post("/api/resume/me/experience", json=_experience_payload(), headers=auth_headers)
    await async_client.post("/api/resume/me/education", json=_education_payload(), headers=auth_headers)
    await async_client.post("/api/resume/me/projects", json=_project_payload(), headers=auth_headers)

    response = await async_client.get("/api/resume/public/public-slug")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "public-slug"
    assert len(body["experience"]) == 1
    assert len(body["education"]) == 1
    assert len(body["projects"]) == 1


async def test_public_resume_nonexistent_slug(async_client):
    response = await async_client.get("/api/resume/public/no-such-slug")
    assert response.status_code == 404


async def test_public_resume_no_auth_required(async_client, auth_headers):
    await async_client.put("/api/resume/me", json=_resume_payload(slug="open-slug"), headers=auth_headers)

    response = await async_client.get("/api/resume/public/open-slug")

    assert response.status_code == 200

# ---- photo resume ----

async def test_upload_photo(async_client, make_verified_user):
    user, headers = await make_verified_user("photo-user@example.com")
    await async_client.put("/api/resume/me", json=_resume_payload(slug="photo-user"), headers=headers)

    fake_photo = BytesIO(b"fake image bytes")

    with patch("app.api.endpoints.resume.upload_photo", return_value="http://minio/test.jpg"):
        response = await async_client.post(
            "/api/resume/me/photo",
            files={"file": ("photo.jpg", fake_photo, "image/jpeg")},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["photo_url"] == "http://minio/test.jpg"


async def test_upload_photo_without_resume(async_client, auth_headers):
    fake_photo = BytesIO(b"fake image bytes")

    response = await async_client.post(
        "/api/resume/me/photo",
        files={"file": ("photo.jpg", fake_photo, "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 404


async def test_update_resume_does_not_clear_photo(async_client, make_verified_user):
    _, headers = await make_verified_user("photo-keep@example.com")
    await async_client.put("/api/resume/me", json=_resume_payload(slug="photo-keep"), headers=headers)

    fake_photo = BytesIO(b"fake image bytes")
    with patch("app.api.endpoints.resume.upload_photo", return_value="http://minio/keep.jpg"):
        await async_client.post(
            "/api/resume/me/photo",
            files={"file": ("photo.jpg", fake_photo, "image/jpeg")},
            headers=headers,
        )

    response = await async_client.put(
        "/api/resume/me",
        json=_resume_payload(slug="photo-keep", full_name="Photo Keep Updated"),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["photo_url"] == "http://minio/keep.jpg"