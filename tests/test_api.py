import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_login():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/login")
        assert response.status_code == 200
        assert "access_token" in response.json()
