"""Compare article identities without confusing related coverage with the source."""
from urllib.parse import parse_qsl, urlencode, urlsplit


def article_identity(url):
    parsed = urlsplit(url or "")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    query = [(key, value) for key, value in parse_qsl(parsed.query)
             if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "ref"}]
    return host, parsed.path.rstrip("/"), urlencode(sorted(query))


def same_article_url(left, right):
    return bool(urlsplit(left or "").hostname) and article_identity(left) == article_identity(right)
