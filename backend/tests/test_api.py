import os
os.environ["DATABASE_URL"]="sqlite:///./data/test.db"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()=={"status":"ok"}
def test_bad_admin(): assert client.post("/api/admin/ingest",headers={"X-Admin-Token":"wrong"}).status_code==401
