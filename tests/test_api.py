import asyncio

import httpx

from cloudpe.web import app


def test_health_and_gallery():
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.get("/api/health")).json() == {"status": "ok"}
            examples = (await client.get("/api/examples")).json()
            assert len(examples) == 6
            assert {e["id"] for e in examples} == {
                "bunny",
                "fachada",
                "esfera",
                "esquina",
                "cuadra_dense",
                "cuadra_sparse",
            }

    asyncio.run(check())


def test_api_rejects_unsafe_requests():
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/jobs",
                json={"operation": "open", "example": "bunny", "params": {"budget": 5000000}},
            )
            assert response.status_code == 400
            response = await client.post(
                "/api/jobs",
                headers={"Origin": "https://untrusted.example"},
                json={"operation": "open", "example": "bunny"},
            )
            assert response.status_code == 403
            assert (await client.get("/api/projects/invalid/points.bin")).status_code == 404

    asyncio.run(check())
