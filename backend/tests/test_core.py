from datetime import datetime, timezone
from app.services.news import canonicalize, clean
from app.services.ai import semantic_check

def test_url_and_content_normalization():
    assert canonicalize("https://example.com/a/?utm_source=x") == "https://example.com/a"
    assert clean("<b>Hallo</b>   Welt") == "Hallo Welt"
def test_semantic_check_accepts_phrasing():
    assert semantic_check("Die Nachricht handelt von Berlin", "Berlin Nachricht")
    assert not semantic_check("Das Wetter ist schön", "Berlin Nachricht")
