"""
Tests de la API de Leads.

Ejecutar:
    pytest tests/ -v

Los tests usan una base de datos SQLite en memoria para no requerir PostgreSQL.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app

# In-memory SQLite for tests

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/token", json={"username": "admin", "password": "onemillion2026"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


# Helper

async def create_sample_lead(client: AsyncClient, headers: dict, overrides: dict = {}) -> dict:
    data = {
        "nombre": "Test User",
        "email": "test@example.com",
        "fuente": "instagram",
        **overrides,
    }
    resp = await client.post("/leads", json=data, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# Tests

class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post("/auth/token", json={"username": "admin", "password": "onemillion2026"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post("/auth/token", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        resp = await client.get("/leads")
        assert resp.status_code == 401


class TestCreateLead:
    async def test_create_lead_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/leads",
            json={"nombre": "Ana García", "email": "ana@example.com", "fuente": "facebook"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "ana@example.com"
        assert body["fuente"] == "facebook"
        assert "id" in body

    async def test_create_lead_duplicate_email(self, client: AsyncClient, auth_headers: dict):
        await create_sample_lead(client, auth_headers)
        resp = await client.post(
            "/leads",
            json={"nombre": "Otro User", "email": "test@example.com", "fuente": "instagram"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_create_lead_invalid_email(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/leads",
            json={"nombre": "Test", "email": "not-an-email", "fuente": "instagram"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_lead_invalid_fuente(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/leads",
            json={"nombre": "Test", "email": "test2@example.com", "fuente": "tiktok"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_lead_nombre_too_short(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/leads",
            json={"nombre": "A", "email": "short@example.com", "fuente": "instagram"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestListLeads:
    async def test_list_leads_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/leads", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["data"] == []

    async def test_list_leads_pagination(self, client: AsyncClient, auth_headers: dict):
        # Create 3 leads
        for i in range(3):
            await create_sample_lead(
                client, auth_headers,
                {"email": f"user{i}@example.com", "nombre": f"User {i}"}
            )
        resp = await client.get("/leads?page=1&limit=2", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["data"]) == 2
        assert body["pages"] == 2

    async def test_list_leads_filter_by_fuente(self, client: AsyncClient, auth_headers: dict):
        await create_sample_lead(client, auth_headers, {"email": "ig@example.com", "fuente": "instagram"})
        await create_sample_lead(client, auth_headers, {"email": "fb@example.com", "fuente": "facebook"})

        resp = await client.get("/leads?fuente=instagram", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["data"][0]["fuente"] == "instagram"


class TestGetLead:
    async def test_get_lead_success(self, client: AsyncClient, auth_headers: dict):
        lead = await create_sample_lead(client, auth_headers)
        resp = await client.get(f"/leads/{lead['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == lead["id"]

    async def test_get_lead_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/leads/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert resp.status_code == 404


class TestUpdateLead:
    async def test_update_lead_success(self, client: AsyncClient, auth_headers: dict):
        lead = await create_sample_lead(client, auth_headers)
        resp = await client.patch(
            f"/leads/{lead['id']}",
            json={"presupuesto": 999.0, "producto_interes": "Mentoría"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["presupuesto"] == 999.0
        assert body["producto_interes"] == "Mentoría"

    async def test_update_lead_email_conflict(self, client: AsyncClient, auth_headers: dict):
        lead1 = await create_sample_lead(client, auth_headers, {"email": "a@example.com"})
        lead2 = await create_sample_lead(
            client, auth_headers,
            {"email": "b@example.com", "nombre": "Other User"}
        )
        resp = await client.patch(
            f"/leads/{lead2['id']}",
            json={"email": "a@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 409


class TestDeleteLead:
    async def test_soft_delete_lead(self, client: AsyncClient, auth_headers: dict):
        lead = await create_sample_lead(client, auth_headers)
        resp = await client.delete(f"/leads/{lead['id']}", headers=auth_headers)
        assert resp.status_code == 204

        # Should not be retrievable after soft delete
        resp2 = await client.get(f"/leads/{lead['id']}", headers=auth_headers)
        assert resp2.status_code == 404


class TestStats:
    async def test_stats_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/leads/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_leads"] == 0
        assert body["leads_por_fuente"] == []
        assert body["promedio_presupuesto"] is None
        assert body["leads_ultimos_7_dias"] == 0

    async def test_stats_with_data(self, client: AsyncClient, auth_headers: dict):
        await create_sample_lead(
            client, auth_headers,
            {"email": "s1@example.com", "fuente": "instagram", "presupuesto": 100}
        )
        await create_sample_lead(
            client, auth_headers,
            {"email": "s2@example.com", "fuente": "facebook", "presupuesto": 200}
        )
        resp = await client.get("/leads/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_leads"] == 2
        assert body["promedio_presupuesto"] == 150.0
        assert body["leads_ultimos_7_dias"] == 2
        assert len(body["leads_por_fuente"]) == 2


class TestWebhook:
    async def test_webhook_creates_lead(self, client: AsyncClient):
        payload = {
            "form_id": "tf_abc123",
            "token": "tok_xyz",
            "submitted_at": "2024-06-01T10:00:00Z",
            "answers": [
                {"field_id": "nombre", "value": "Webhook User"},
                {"field_id": "email", "value": "webhook@example.com"},
                {"field_id": "fuente", "value": "landing_page"},
                {"field_id": "presupuesto", "value": "500"},
            ],
        }
        resp = await client.post("/leads/webhook", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "webhook@example.com"
        assert body["fuente"] == "landing_page"
