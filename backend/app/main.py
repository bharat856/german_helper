from datetime import datetime, timezone
import time
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from .db import Base, engine, get_db, migrate_sqlite
from .models import Article, Adaptation, Quiz, QuizAttempt, Vocabulary, SettingsRow, NewsRefresh
from .schemas import AdaptedArticle, ArticleOut, Level, SettingsIn, SubmitQuiz
from .services.ai import AIProvider, semantic_check
from .services.news import NewsProviderError, fetch_news
from .config import get_settings

Base.metadata.create_all(engine); migrate_sqlite(); app=FastAPI(title="German Helper API")
app.add_middleware(CORSMiddleware, allow_origins=[get_settings().frontend_origin,"http://localhost:5173","http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
_last_refresh_monotonic = 0.0
def public_quiz(q):
    return {"id":q.id,"questions":[{k:v for k,v in x.items() if k not in {"correct_index","suggested_answer","explanation"}} for x in q.questions]}
@app.get("/api/news/today", response_model=list[ArticleOut])
def today(db:Session=Depends(get_db)):
    settings = get_settings()
    return db.scalars(select(Article).where(Article.is_demo.is_(False), Article.provider == settings.news_provider).order_by(desc(Article.publication_date)).limit(settings.news_max_articles)).all()
@app.get("/api/news/history", response_model=list[ArticleOut])
def history(db:Session=Depends(get_db)): return db.scalars(select(Article).where(Article.is_demo.is_(False)).order_by(desc(Article.publication_date))).all()
@app.get("/api/news/status")
def news_status(db:Session=Depends(get_db)):
    row = db.get(NewsRefresh, 1)
    return {"provider": get_settings().news_provider, "last_success_at": row.last_success_at if row else None,
            "last_error": row.last_error if row else None, "articles_count": row.articles_count if row else 0,
            "delay_note": "GNews free plans may publish headlines with up to a 12-hour delay."}
@app.get("/api/articles/{article_id}")
def article(article_id:int, db:Session=Depends(get_db)):
    a=db.get(Article,article_id)
    if not a: raise HTTPException(404,"Article not found")
    return {"article":ArticleOut.model_validate(a),"adaptations":[AdaptedArticle(title=x.title,level=x.level,adapted_article=x.adapted_article,vocabulary=x.vocabulary,source_url=a.source_url,source_name=a.source_name,publication_date=a.publication_date) for x in a.adaptations]}
@app.post("/api/articles/{article_id}/adapt", response_model=AdaptedArticle)
def adapt(article_id:int, level:Level, db:Session=Depends(get_db)):
    a=db.get(Article,article_id)
    if not a: raise HTTPException(404,"Article not found")
    existing=db.scalar(select(Adaptation).where(Adaptation.article_id==article_id,Adaptation.level==level))
    if not existing:
        source_text = "\n".join(part for part in (a.content, a.description) if part).strip()
        if len(source_text) < 80:
            raise HTTPException(422, "This article does not contain enough source text for a reliable adaptation.")
        try: data=AIProvider().adapt(a,level)
        except RuntimeError as exc: raise HTTPException(503,str(exc))
        existing=Adaptation(article=a,level=level,title=data.title,adapted_article=data.adapted_article,vocabulary=data.vocabulary); db.add(existing); db.flush()
        for item in data.vocabulary:
            vocab = db.scalar(select(Vocabulary).where(Vocabulary.german == item["german"]))
            if vocab:
                vocab.article = item.get("article")
                vocab.english = item["english"]
                vocab.example = item["example"]
            else:
                db.add(Vocabulary(german=item["german"], article=item.get("article"), english=item["english"], example=item["example"]))
        db.commit()
    return AdaptedArticle(title=existing.title,level=existing.level,adapted_article=existing.adapted_article,vocabulary=existing.vocabulary,source_url=a.source_url,source_name=a.source_name,publication_date=a.publication_date)
@app.get("/api/articles/{article_id}/quiz")
def get_quiz(article_id:int, level:Level, db:Session=Depends(get_db)):
    ad=db.scalar(select(Adaptation).where(Adaptation.article_id==article_id,Adaptation.level==level))
    if not ad: raise HTTPException(404,"Adapt the article first")
    q=db.scalar(select(Quiz).where(Quiz.adaptation_id==ad.id))
    if not q:
        q=Quiz(adaptation=ad,questions=AIProvider().quiz(ad)); db.add(q); db.commit(); db.refresh(q)
    return public_quiz(q)
@app.post("/api/quizzes/{quiz_id}/submit")
def submit(quiz_id:int, payload:SubmitQuiz, db:Session=Depends(get_db)):
    q=db.get(Quiz,quiz_id)
    if not q: raise HTTPException(404,"Quiz not found")
    results=[]
    for item, answer in zip(q.questions,payload.answers):
        if item["type"]=="mcq":
            correct=answer==str(item.get("correct_index")); evaluation={"correct":correct,"feedback":item["explanation"] if correct else "Lies den Abschnitt noch einmal.","suggested_answer":item["options"][item["correct_index"]],"grammar_corrections":[]}
        else:
            evaluation=AIProvider().evaluate_free_text(answer,item.get("suggested_answer",""),q.adaptation.level)
            if isinstance(evaluation,str): evaluation={"correct":semantic_check(answer,item.get("suggested_answer","")),"feedback":evaluation,"suggested_answer":item.get("suggested_answer",""),"grammar_corrections":[]}
        results.append(evaluation)
    score=round(sum(r["correct"] for r in results)/len(results)*100); db.add(QuizAttempt(quiz=q,answers=payload.answers,results=results,score=score)); db.commit(); return {"score":score,"results":results}
@app.get("/api/progress")
def progress(db:Session=Depends(get_db)):
    attempts=db.scalars(select(QuizAttempt).order_by(desc(QuizAttempt.completed_at))).all(); return {"completed_articles":len(attempts),"quiz_history":[{"score":a.score,"completed_at":a.completed_at,"quiz_id":a.quiz_id} for a in attempts],"average_score":round(sum(a.score for a in attempts)/len(attempts)) if attempts else 0,"reading_streak":len({a.completed_at.date() for a in attempts})}
@app.get("/api/vocabulary")
def vocabulary(db:Session=Depends(get_db)): return db.scalars(select(Vocabulary).order_by(desc(Vocabulary.created_at))).all()
@app.put("/api/settings")
def settings(payload:SettingsIn, db:Session=Depends(get_db)):
    row=db.get(SettingsRow,1) or SettingsRow(id=1); row.preferred_level=payload.preferred_level; row.translations=payload.translations; row.feedback_language=payload.feedback_language; db.add(row); db.commit(); return payload
def _ingest(db: Session):
    global _last_refresh_monotonic
    now = time.monotonic()
    if now - _last_refresh_monotonic < get_settings().news_refresh_min_seconds:
        retry = int(get_settings().news_refresh_min_seconds - (now - _last_refresh_monotonic))
        raise HTTPException(429, f"News was refreshed recently. Try again in {retry} seconds.")
    _last_refresh_monotonic = now
    row = db.get(NewsRefresh, 1) or NewsRefresh(id=1, provider=get_settings().news_provider)
    try:
        items = fetch_news()
        added = updated = 0
        for data in items:
            existing = db.scalar(select(Article).where(Article.canonical_url == data["canonical_url"]))
            if existing:
                for key, value in data.items():
                    if key not in {"is_demo", "canonical_url"}:
                        setattr(existing, key, value)
                existing.is_demo = False
                updated += 1
            else:
                db.add(Article(**data)); added += 1
        row.provider = get_settings().news_provider
        row.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None)
        row.last_error = None
        row.articles_count = len(items)
        db.add(row); db.commit()
        return {"added": added, "updated": updated, "articles_count": len(items), "last_success_at": row.last_success_at,
                "provider": get_settings().news_provider}
    except NewsProviderError as exc:
        row.last_error = str(exc); row.provider = get_settings().news_provider; db.add(row); db.commit()
        raise HTTPException(exc.status_code, str(exc)) from exc

@app.post("/api/news/refresh")
def refresh_news(db:Session=Depends(get_db)):
    return _ingest(db)

@app.post("/api/admin/ingest")
def ingest(x_admin_token:str|None=Header(default=None), db:Session=Depends(get_db)):
    if x_admin_token != get_settings().admin_token: raise HTTPException(401,"Invalid admin token")
    return _ingest(db)
@app.get("/health")
def health(): return {"status":"ok"}
