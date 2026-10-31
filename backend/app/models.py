from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    source_name: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(1000), unique=True)
    canonical_url: Mapped[str] = mapped_column(String(1000), index=True)
    publication_date: Mapped[datetime] = mapped_column(DateTime)
    category: Mapped[str] = mapped_column(String(50), default="Nachrichten")
    content: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    provider: Mapped[str] = mapped_column(String(30), default="rss")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    adaptations = relationship("Adaptation", back_populates="article", cascade="all, delete-orphan")

class Adaptation(Base):
    __tablename__ = "adaptations"
    __table_args__ = (UniqueConstraint("article_id", "level"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    level: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(300))
    adapted_article: Mapped[str] = mapped_column(Text)
    vocabulary: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    article = relationship("Article", back_populates="adaptations")
    quizzes = relationship("Quiz", back_populates="adaptation", cascade="all, delete-orphan")

class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[int] = mapped_column(primary_key=True)
    adaptation_id: Mapped[int] = mapped_column(ForeignKey("adaptations.id"))
    questions: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    adaptation = relationship("Adaptation", back_populates="quizzes")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    answers: Mapped[list] = mapped_column(JSON)
    results: Mapped[list] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    quiz = relationship("Quiz", back_populates="attempts")

class Vocabulary(Base):
    __tablename__ = "vocabulary"
    id: Mapped[int] = mapped_column(primary_key=True)
    german: Mapped[str] = mapped_column(String(100), unique=True)
    article: Mapped[str | None] = mapped_column(String(10), nullable=True)
    english: Mapped[str] = mapped_column(String(200))
    example: Mapped[str] = mapped_column(String(500))
    saved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SettingsRow(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    preferred_level: Mapped[str] = mapped_column(String(2), default="B1")
    translations: Mapped[bool] = mapped_column(Boolean, default=True)
    feedback_language: Mapped[str] = mapped_column(String(20), default="English")

class NewsRefresh(Base):
    __tablename__ = "news_refreshes"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(30), default="gnews")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    articles_count: Mapped[int] = mapped_column(Integer, default=0)
