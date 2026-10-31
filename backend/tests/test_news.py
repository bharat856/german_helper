from datetime import timezone
import requests
import pytest

from app.services.news import GNewsProvider, InvalidNewsKey, NewsRateLimited, NewsProviderError, parse_publication_date

class FakeSettings:
    gnews_api_key = "test-key"
    news_language = "de"
    news_country = "de"
    news_max_articles = 10

class FakeResponse:
    def __init__(self, status=200, payload=None): self.status_code, self.payload = status, payload or {}
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError(response=self)
    def json(self): return self.payload

class FakeSession:
    def __init__(self, response): self.response = response; self.params = None
    def get(self, url, params, timeout, headers): self.params = params; return self.response

def payload():
    return {"articles":[{"title":"Echte Nachricht","description":"Eine kurze Zusammenfassung.","content":"Eine längere Inhaltsprobe mit ausreichend Informationen für die Lernansicht.","url":"https://example.de/story?utm_source=test","image":"https://example.de/image.jpg","publishedAt":"2026-10-31T10:15:00Z","source":{"name":"Beispiel News"}}, {"title":"Duplikat","description":"","content":"","url":"https://example.de/story","publishedAt":"2026-10-31T10:16:00Z","source":{"name":"Beispiel News"}}]}

def test_gnews_success_normalizes_and_deduplicates():
    session = FakeSession(FakeResponse(payload=payload()))
    articles = GNewsProvider(FakeSettings(), session).fetch()
    assert len(articles) == 1
    assert articles[0]["provider"] == "gnews"
    assert articles[0]["source_name"] == "Beispiel News"
    assert articles[0]["publication_date"].tzinfo is None  # SQLite-compatible UTC-naive storage
    assert session.params["lang"] == "de" and session.params["country"] == "de"

def test_publication_date_is_utc_aware_before_storage():
    parsed = parse_publication_date("2026-10-31T10:15:00+02:00")
    assert parsed.tzinfo == timezone.utc and parsed.hour == 8

@pytest.mark.parametrize("status,error", [(401, InvalidNewsKey), (403, InvalidNewsKey), (429, NewsRateLimited), (500, NewsProviderError)])
def test_gnews_provider_errors(status, error):
    with pytest.raises(error): GNewsProvider(FakeSettings(), FakeSession(FakeResponse(status=status))).fetch()

def test_gnews_network_failure():
    class BrokenSession:
        def get(self, *args, **kwargs): raise requests.Timeout("offline")
    with pytest.raises(NewsProviderError, match="network failure"): GNewsProvider(FakeSettings(), BrokenSession()).fetch()

def test_missing_api_key():
    class NoKey(FakeSettings): gnews_api_key = None
    with pytest.raises(InvalidNewsKey): GNewsProvider(NoKey(), FakeSession(FakeResponse())).fetch()

def test_empty_results():
    assert GNewsProvider(FakeSettings(), FakeSession(FakeResponse(payload={"articles":[]}))).fetch() == []
