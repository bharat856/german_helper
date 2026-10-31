from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit
import feedparser, html, re, requests
from ..config import get_settings

FEEDS = [("Tagesschau","https://www.tagesschau.de/xml/rss2"),("DW","https://rss.dw.com/rdf/rss-de-all")]
def canonicalize(url):
    p=urlsplit(url); return urlunsplit((p.scheme,p.netloc,p.path.rstrip('/'),'',''))
def clean(text): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>"," ",text or ""))).strip()
def fetch_entries(feeds=FEEDS, now=None):
    now=now or datetime.now(timezone.utc); cutoff=now-timedelta(days=2); found=[]; seen=set()
    for source, url in feeds:
        try:
            data=requests.get(url, timeout=12, headers={"User-Agent":"GermanHelper/1.0"}); data.raise_for_status(); parsed=feedparser.parse(data.content)
        except requests.RequestException: continue
        for e in parsed.entries:
            link=canonicalize(e.get("link","")); title=clean(e.get("title","")); key=(link or title.lower())
            if not title or not link or key in seen: continue
            stamp=e.get("published_parsed") or e.get("updated_parsed")
            published=datetime(*stamp[:6],tzinfo=timezone.utc) if stamp else now
            if published < cutoff: continue
            seen.add(key); found.append({"title":title[:300],"description":clean(e.get("summary", ""))[:4000],"source_name":source,"source_url":link,"canonical_url":link,"publication_date":published.replace(tzinfo=None),"category":"Nachrichten"})
    return found[:get_settings().max_daily_articles]
