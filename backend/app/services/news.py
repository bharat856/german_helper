from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

from ..config import get_settings

FEEDS = [("Tagesschau", "https://www.tagesschau.de/xml/rss2"), ("DW", "https://rss.dw.com/rdf/rss-de-all")]

class NewsProviderError(RuntimeError):
    status_code = 502

class InvalidNewsKey(NewsProviderError):
    status_code = 401

class NewsRateLimited(NewsProviderError):
    status_code = 429

class NewsProvider(Protocol):
    name: str
    def fetch(self) -> list[dict[str, Any]]: ...

def canonicalize(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))

def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()

def parse_publication_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def normalize_article(*, title: str, description: str, content: str, source_name: str, url: str,
                      image_url: str | None, published_at: str | None, provider: str) -> dict[str, Any] | None:
    title = clean(title)
    canonical_url = canonicalize(url)
    if not title or not canonical_url or not urlsplit(canonical_url).netloc:
        return None
    return {
        "title": title[:300],
        "description": clean(description)[:4000],
        "content": clean(content)[:12000],
        "source_name": clean(source_name)[:100] or "Unbekannte Quelle",
        "source_url": url[:1000],
        "canonical_url": canonical_url,
        "image_url": image_url[:1000] if image_url else None,
        "publication_date": parse_publication_date(published_at).replace(tzinfo=None),
        "category": "Nachrichten",
        "provider": provider,
        "is_demo": False,
    }

class GNewsProvider:
    name = "gnews"
    endpoint = "https://gnews.io/api/v4/top-headlines"

    def __init__(self, settings=None, session: requests.Session | None = None):
        self.settings = settings or get_settings()
        self.session = session or requests.Session()

    def fetch(self) -> list[dict[str, Any]]:
        if not self.settings.gnews_api_key:
            raise InvalidNewsKey("GNEWS_API_KEY is not configured")
        params = {"token": self.settings.gnews_api_key, "lang": self.settings.news_language,
                  "country": self.settings.news_country, "category": "general", "max": self.settings.news_max_articles}
        try:
            response = self.session.get(self.endpoint, params=params, timeout=15, headers={"User-Agent": "GermanHelper/1.0"})
        except requests.RequestException as exc:
            raise NewsProviderError(f"GNews network failure: {exc}") from exc
        if response.status_code in (401, 403):
            raise InvalidNewsKey("GNews rejected the API key")
        if response.status_code == 429:
            raise NewsRateLimited("GNews rate limit reached")
        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise NewsProviderError(f"Invalid GNews response: {exc}") from exc
        articles = []
        seen: set[str] = set()
        for item in payload.get("articles", []):
            source = item.get("source") or {}
            normalized = normalize_article(title=item.get("title", ""), description=item.get("description", ""),
                content=item.get("content", ""), source_name=source.get("name", ""), url=item.get("url", ""),
                image_url=item.get("image"), published_at=item.get("publishedAt"), provider=self.name)
            if normalized and normalized["canonical_url"] not in seen:
                seen.add(normalized["canonical_url"])
                articles.append(normalized)
        return articles[: self.settings.news_max_articles]

class RSSProvider:
    name = "rss"
    def __init__(self, feeds=FEEDS, now=None):
        self.feeds, self.now = feeds, now or datetime.now(timezone.utc)

    def fetch(self) -> list[dict[str, Any]]:
        cutoff = self.now - __import__("datetime").timedelta(days=2)
        found, seen = [], set()
        for source, url in self.feeds:
            try:
                response = requests.get(url, timeout=12, headers={"User-Agent": "GermanHelper/1.0"})
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
            except requests.RequestException:
                continue
            for entry in parsed.entries:
                link = canonicalize(entry.get("link", ""))
                stamp = entry.get("published") or entry.get("updated")
                published = parse_publication_date(stamp)
                if not link or link in seen or published < cutoff:
                    continue
                item = normalize_article(title=entry.get("title", ""), description=entry.get("summary", ""),
                    content=entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
                    source_name=source, url=link, image_url=None, published_at=stamp, provider=self.name)
                if item:
                    seen.add(link)
                    found.append(item)
        return found[: get_settings().news_max_articles]

def get_news_provider() -> NewsProvider:
    settings = get_settings()
    if settings.news_provider.lower() == "rss":
        return RSSProvider()
    return GNewsProvider(settings=settings)

def fetch_news() -> list[dict[str, Any]]:
    settings = get_settings()
    try:
        return get_news_provider().fetch()
    except NewsProviderError:
        if settings.news_rss_fallback and settings.news_provider.lower() == "gnews":
            return RSSProvider().fetch()
        raise
