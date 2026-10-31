import sys
from .db import SessionLocal, Base, engine
from .models import Article
from .services.news import fetch_entries
Base.metadata.create_all(engine)
def main():
    db=SessionLocal(); added=0
    for item in fetch_entries():
        if not db.query(Article).filter_by(canonical_url=item["canonical_url"]).first(): db.add(Article(**item)); added+=1
    db.commit(); print(f"Ingested {added} articles")
if __name__ == "__main__": main()
