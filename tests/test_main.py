from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_add():
    response = client.get("/add", params={"a": 2, "b": 3})
    assert response.json() == {"result": 5}