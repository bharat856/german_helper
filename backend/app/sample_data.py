from datetime import datetime, timezone
from .db import Base, engine, SessionLocal, migrate_sqlite
from .models import Article
Base.metadata.create_all(engine)
migrate_sqlite()
db=SessionLocal()
if not db.query(Article).first():
    db.add_all([Article(title="Deutschland investiert in neue Bildungsideen",description="Neue Programme sollen Schulen und Lernende in Deutschland unterstützen. Die Initiative verbindet digitale Angebote mit persönlicher Betreuung.",content="Neue Programme sollen Schulen und Lernende in Deutschland unterstützen. Die Initiative verbindet digitale Angebote mit persönlicher Betreuung.",source_name="German Helper sample",source_url="https://example.com/education",canonical_url="https://example.com/education",publication_date=datetime.now(timezone.utc).replace(tzinfo=None),category="Gesellschaft",provider="sample",is_demo=True),Article(title="Mehr Grün in deutschen Städten",description="Viele Städte planen neue Parks und Bäume. Das soll die Luft verbessern und im Sommer für kühlere Straßen sorgen.",content="Viele Städte planen neue Parks und Bäume. Das soll die Luft verbessern und im Sommer für kühlere Straßen sorgen.",source_name="German Helper sample",source_url="https://example.com/cities",canonical_url="https://example.com/cities",publication_date=datetime.now(timezone.utc).replace(tzinfo=None),category="Umwelt",provider="sample",is_demo=True)]); db.commit()
print("Sample data ready")
