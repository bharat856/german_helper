import os
os.environ["DATABASE_URL"]="sqlite:///./data/test.db"
os.environ["NEWS_PROVIDER"]="gnews"
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import Article
from datetime import datetime
client=TestClient(app)
def test_health(): assert client.get("/health").json()=={"status":"ok"}
def test_bad_admin(): assert client.post("/api/admin/ingest",headers={"X-Admin-Token":"wrong"}).status_code==401
def test_dashboard_shows_real_and_hides_demo():
    db=SessionLocal()
    db.query(Article).delete()
    db.add(Article(title="Echte GNews Schlagzeile",description="Beschreibung",content="Lange Quelle",source_name="GNews",source_url="https://news.example/1",canonical_url="https://news.example/1",publication_date=datetime.utcnow(),provider="gnews",is_demo=False))
    db.add(Article(title="Demo",description="Demo",source_name="Sample",source_url="https://sample.example",canonical_url="https://sample.example",publication_date=datetime.utcnow(),provider="sample",is_demo=True))
    db.commit(); db.close()
    response=client.get("/api/news/today")
    assert response.status_code==200
    assert [item["title"] for item in response.json()]==["Echte GNews Schlagzeile"]
