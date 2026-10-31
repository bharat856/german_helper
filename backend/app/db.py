from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings, ensure_data_dir

ensure_data_dir()
engine = create_engine(get_settings().database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def migrate_sqlite() -> None:
    if not get_settings().database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "articles" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("articles")}
    additions = {"content": "TEXT DEFAULT ''", "image_url": "VARCHAR(1000)", "provider": "VARCHAR(30) DEFAULT 'rss'", "is_demo": "BOOLEAN DEFAULT 0"}
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE articles ADD COLUMN {name} {definition}"))
        connection.execute(text("UPDATE articles SET is_demo = 1, provider = 'sample' WHERE source_name = 'German Helper sample' OR source_url LIKE 'https://example.com/%'"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
