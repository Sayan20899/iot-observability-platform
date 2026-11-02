import os
os.environ["DATABASE_URL"] = "sqlite:///./test_iot.db"

from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_and_ingest():
    client.delete("/api/demo/reset")
    device = {"device_id":"TEST-001","name":"Test Sensor","location":"Lab"}
    response = client.post("/api/devices", json=device)
    assert response.status_code == 201
    reading = {"device_id":"TEST-001","temperature":42.5,"humidity":88,"power":25}
    response = client.post("/api/telemetry", json=reading)
    assert response.status_code == 201
    assert client.get("/api/summary").json()["total_readings"] == 1
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 2
