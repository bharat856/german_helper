from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Level = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

class VocabularyItem(BaseModel):
    german: str
    article: str | None = None
    english: str
    example: str

class ArticleOut(BaseModel):
    id: int; title: str; description: str; source_name: str; source_url: str; publication_date: datetime; category: str
    model_config = ConfigDict(from_attributes=True)

class AdaptedArticle(BaseModel):
    title: str; level: Level; adapted_article: str; vocabulary: list[VocabularyItem]; source_url: str; source_name: str; publication_date: datetime

class SubmitQuiz(BaseModel):
    answers: list[str] = Field(min_length=5, max_length=5)

class SettingsIn(BaseModel):
    preferred_level: Level = "B1"; translations: bool = True; feedback_language: Literal["English", "German"] = "English"
