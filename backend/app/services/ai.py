import json, re, time
from datetime import datetime
from pydantic import BaseModel, ValidationError
from ..config import get_settings

LEVEL_GUIDANCE = {
    "A1":"Short, simple sentences; common vocabulary; mostly present tense.", "A2":"Simple connected sentences; everyday vocabulary; basic past tense.",
    "B1":"Intermediate vocabulary; longer explanations; common subordinate clauses.", "B2":"Complex syntax, nuanced explanations, broad vocabulary.",
    "C1":"Advanced language and sophisticated sentence structures.", "C2":"Near-native complexity, nuanced vocabulary and idiomatic expressions."
}
class AIAdaptation(BaseModel):
    title: str; adapted_article: str; vocabulary: list[dict]

class AIProvider:
    def __init__(self): self.settings = get_settings()
    def _mock(self, article, level):
        sentence = article.description.strip() or article.title
        return AIAdaptation(title=article.title, adapted_article=f"{sentence}\n\nDieser Text ist eine KI-angepasste Zusammenfassung auf Niveau {level}.", vocabulary=[{"german":"die Nachricht","article":"die","english":"the news","example":"Ich lese die Nachricht."},{"german":"wichtig","article":None,"english":"important","example":"Das Thema ist wichtig."}])
    def adapt(self, article, level):
        if not self.settings.gemini_api_key: return self._mock(article, level)
        try:
            from google import genai
            client = genai.Client(api_key=self.settings.gemini_api_key)
            prompt = f"""Rewrite this news item in German at CEFR {level}. {LEVEL_GUIDANCE[level]} Preserve every fact, date, number and attribution; never invent quotes or events. Use only the supplied text. Return JSON with title, adapted_article, vocabulary (objects german, article, english, example). Label nothing as original reporting.\nTitle: {article.title}\nSummary: {article.description}"""
            for attempt in range(3):
                try:
                    response = client.models.generate_content(model=self.settings.gemini_model, contents=prompt, config={"response_mime_type":"application/json"})
                    return AIAdaptation.model_validate_json(response.text)
                except Exception:
                    if attempt == 2: raise
                    time.sleep(2 ** attempt)
        except Exception as exc:
            raise RuntimeError(f"Gemini unavailable: {exc}") from exc

    def quiz(self, adaptation):
        # Deterministic local fallback keeps the MVP useful without a key.
        return [{"type":"mcq","question":"Was ist das Hauptthema des Textes?","options":[adaptation.title,"Das Wetter","Ein Kochrezept","Ein Sportspiel"],"correct_index":0,"explanation":"Der Titel nennt das Hauptthema."},{"type":"mcq","question":"Welche Quelle wird genannt?","options":["Die angegebene Nachricht","Ein Roman","Ein Film","Keine Quelle"],"correct_index":0,"explanation":"Die Quelle steht unter dem Artikel."},{"type":"mcq","question":"Auf welchem Niveau wurde der Text angepasst?","options":[adaptation.level if hasattr(adaptation,'level') else "B1","C2","A1","Keinem"],"correct_index":0,"explanation":"Das gewählte Niveau wird angezeigt."},{"type":"text","question":"Nenne ein wichtiges Wort aus dem Text.","suggested_answer":adaptation.vocabulary[0]['german'],"explanation":"Ein passendes Wort aus der Wortliste ist richtig."},{"type":"text","question":"Was hast du über das Thema gelernt?","suggested_answer":adaptation.title,"explanation":"Eine inhaltlich passende Antwort ist richtig."}]

    def evaluate_free_text(self, answer: str, expected: str, level: str):
        if not self.settings.gemini_api_key:
            ok = semantic_check(answer, expected)
            return {"correct": ok, "feedback": "Deine Antwort zeigt gutes Verständnis." if ok else "Vergleiche deine Antwort noch einmal mit dem Artikel.", "suggested_answer": expected, "grammar_corrections": []}
        from google import genai
        client = genai.Client(api_key=self.settings.gemini_api_key)
        prompt = f"Evaluate a German learner answer at CEFR {level}. Accept valid paraphrases and do not penalize minor grammar if comprehension is correct. Return JSON with correct boolean, supportive feedback, suggested_answer, grammar_corrections list. Expected meaning: {expected}. Learner answer: {answer}"
        response = client.models.generate_content(model=self.settings.gemini_model, contents=prompt, config={"response_mime_type":"application/json"})
        return response.parsed or response.text

def semantic_check(answer: str, expected: str) -> bool:
    a = set(re.findall(r"[a-zA-ZäöüÄÖÜß]+", answer.lower())); e = set(re.findall(r"[a-zA-ZäöüÄÖÜß]+", expected.lower()))
    return bool(a & e) and len(a & e) / max(1, len(e)) >= .5
