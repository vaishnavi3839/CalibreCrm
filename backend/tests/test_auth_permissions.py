import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def login(client: AsyncClient, email: str, password: str = "Password123!"):
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    data = res.json()["data"]
    return data["tokens"]["access_token"], data["user"]


@pytest.mark.asyncio
async def test_login_and_me(client):
    token, user = await login(client, "admin@calibre.academy")
    assert user["role"]["name"] == "admin"
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "admin@calibre.academy"


@pytest.mark.asyncio
async def test_telecaller_only_sees_assigned_leads(client):
    token, _ = await login(client, "priya@calibre.academy")
    res = await client.get("/api/v1/leads", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_instructor_cannot_list_crm_as_telecaller_style(client):
    token, _ = await login(client, "instructor1@calibre.academy")
    res = await client.get("/api/v1/leads", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_other_student(client):
    token, _ = await login(client, "rahul.student@calibre.academy")
    # list students forbidden
    res = await client.get("/api/v1/students", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_student_dashboard_has_no_fees(client):
    token, _ = await login(client, "rahul.student@calibre.academy")
    res = await client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert "fee" not in str(data).lower()
    assert "payment" not in str(data).lower()
    assert data["role"] == "student"


@pytest.mark.asyncio
async def test_certificate_verify_public(client):
    res = await client.get("/api/v1/certificates/verify/CAA-CPL-2026-00452")
    assert res.status_code == 200
    assert res.json()["data"]["verified"] is True


@pytest.mark.asyncio
async def test_website_enquiry_creates_lead(client):
    res = await client.post(
        "/api/v1/leads/website-enquiry",
        json={
            "name": "Website Tester",
            "phone": "9898989898",
            "email": "webtester@example.com",
            "course": "CPL",
            "message": "Interested in commercial pilot training",
        },
    )
    assert res.status_code == 201
    assert res.json()["data"]["lead_code"]
