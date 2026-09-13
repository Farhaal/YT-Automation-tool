from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_generate_stub():
    response = client.post("/generate", json={"text": "Hello world"})
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert response.json()["status"] == "queued"
