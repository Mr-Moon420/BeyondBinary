# main.py
"""
FastAPI application for BeyondBinary credibility and media bias analysis.
Exposes endpoints for full article analysis (claims, verification, and bias),
status, health, and trending news feed.
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from googlenewsdecoder import gnewsdecoder
from pydantic import BaseModel

from claim_extractor import extract_claims
from scorer import compute_score
from search_provider import get_search_provider
from verifier import verify_claim
from bias_detector import analyze_bias
from article_fetcher import fetch_article_from_url, is_valid_url

logger = logging.getLogger("BeyondBinary.Trending")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Load AllSides ratings for publisher bias lookup
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ALLSIDES_FILE = os.path.join(_BASE_DIR, "data", "allsides_ratings.json")
_ALLSIDES: Dict[str, Dict[str, Any]] = {}
try:
    with open(_ALLSIDES_FILE, "r", encoding="utf-8") as f:
        _ALLSIDES = json.load(f)
except Exception:
    pass


def _extract_domain(url: str) -> str:
    """Extract clean base domain from URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or ""
        netloc = netloc.split(":")[0].lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _lookup_publisher(url: str) -> Dict[str, Any]:
    """Look up publisher info and political bias from AllSides."""
    domain = _extract_domain(url)
    if domain in _ALLSIDES:
        info = _ALLSIDES[domain]
        return {
            "domain": domain,
            "name": info.get("name", domain),
            "bias": info.get("bias", "Unrated"),
            "score": info.get("score", None)
        }
    # Try subdomain stripping
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in _ALLSIDES:
            info = _ALLSIDES[parent]
            return {
                "domain": domain,
                "name": info.get("name", parent),
                "bias": info.get("bias", "Unrated"),
                "score": info.get("score", None)
            }
    return {"domain": domain, "name": domain, "bias": "Unrated", "score": None}

app = FastAPI(
    title="BeyondBinary API",
    description="Multi-Dimensional Media Credibility & Bias Analysis API",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArticleInput(BaseModel):
    text: Optional[str] = ""
    url: Optional[str] = None


class UrlInput(BaseModel):
    url: str


@app.get("/")
def root():
    provider = get_search_provider()
    return {
        "project": "BeyondBinary",
        "status": "online",
        "modules": {
            "claim_extractor": "ClaimBuster-DeBERTaV2",
            "verifier": "RoBERTa-large-MNLI + FAISS",
            "search_provider": "Brave Search" if provider.is_configured else "Local FAISS Index",
            "bias_detector": "BERT (theArif/mbzuai-political-bias-bert) + AllSides KB",
            "article_fetcher": "Direct URL Ingestion & Parser"
        }
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fetch-url")
def fetch_url(data: UrlInput):
    """Fetches clean text and metadata from a news article URL."""
    return fetch_article_from_url(data.url)


@app.post("/analyze")
def analyze(article: ArticleInput):
    input_text = (article.text or "").strip()
    source_url = article.url
    article_title = ""

    # 1. Auto-detect if input is a URL or if text is omitted with a URL provided
    if is_valid_url(input_text):
        source_url = input_text
        fetch_res = fetch_article_from_url(source_url)
        if not fetch_res["success"]:
            return {
                "error": fetch_res["error"],
                "credibility_score": 0.0,
                "claims": [],
                "bias_analysis": None
            }
        input_text = fetch_res["text"]
        article_title = fetch_res["title"]
    elif source_url and not input_text:
        fetch_res = fetch_article_from_url(source_url)
        if not fetch_res["success"]:
            return {
                "error": fetch_res["error"],
                "credibility_score": 0.0,
                "claims": [],
                "bias_analysis": None
            }
        input_text = fetch_res["text"]
        article_title = fetch_res["title"]

    if not input_text:
        return {
            "error": "No article text provided to analyze.",
            "credibility_score": 0.0,
            "claims": [],
            "bias_analysis": None
        }

    # 2. Claim extraction
    claims = extract_claims(input_text)

    # 3. Evidence retrieval & NLI verification
    verified_claims = [verify_claim(c) for c in claims[:5]]
    credibility_score = compute_score(verified_claims)

    # Collect retrieved evidence sources for cross-source bias grounding
    collected_sources = []
    for c in verified_claims:
        collected_sources.extend(c.get("sources", []))

    # 4. Political Bias & Framing Analysis
    bias_result = analyze_bias(
        text=input_text,
        source_url=source_url,
        evidence_sources=collected_sources
    )

    provider = get_search_provider()
    search_status = "Brave Search" if provider.is_configured else "Local FAISS Index"

    return {
        "title": article_title,
        "source_url": source_url,
        "credibility_score": credibility_score,
        "claims": verified_claims,
        "bias_analysis": bias_result,
        "extractor": "ClaimBuster-DeBERTaV2",
        "search_provider": search_status
    }


# ── Trending News Feed ──────────────────────────────────────────────

TRENDING_QUERIES = {
    "politics": "latest political news articles today",
    "sports": "latest sports news articles today",
    "tech": "latest technology news articles today"
}


@app.get("/trending")
def trending(topic: Optional[str] = None):
    """
    Fetches trending news headlines via Google News RSS and decodes article URLs.
    Optional query param: ?topic=politics|sports|tech
    If no topic given, fetches all three.
    """
    import requests as req
    from lxml import etree

    topics_to_fetch = {}
    if topic and topic.lower() in TRENDING_QUERIES:
        topics_to_fetch[topic.lower()] = TRENDING_QUERIES[topic.lower()]
    else:
        topics_to_fetch = dict(TRENDING_QUERIES)

    results = {}
    articles_by_category = {}

    for cat, query in topics_to_fetch.items():
        try:
            # Google News RSS search endpoint
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }

            resp = req.get(rss_url, headers=headers, timeout=10.0)

            if resp.status_code != 200:
                logger.warning("Google News RSS fetch failed for '%s': HTTP %d", cat, resp.status_code)
                results[cat] = []
                continue

            # Use etree for proper XML parsing of RSS feeds
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(resp.content, parser=parser)

            # RSS items are usually in //channel/item
            items = root.xpath('//item')

            articles_data = []
            for item in items:
                def get_text(tag):
                    res = item.xpath(f'./{tag}/text()')
                    return res[0].strip() if res else ""

                title_raw = get_text('title')
                link = get_text('link')
                pub_date = get_text('pubDate')
                description = get_text('description')

                if not title_raw or not link:
                    continue

                # Clean the title (Google News adds " - Source Name" to titles)
                article_title = title_raw
                source_name = "Unknown"
                if " - " in title_raw:
                    parts = title_raw.rsplit(" - ", 1)
                    article_title = parts[0].strip()
                    source_name = parts[1].strip()

                articles_data.append({
                    "title": article_title,
                    "link": link,
                    "pub_date": pub_date,
                    "snippet": description,
                    "source_name": source_name
                })

            articles_by_category[cat] = articles_data

        except Exception as e:
            logger.error("Trending fetch error for '%s': %s", cat, e)
            results[cat] = []

    all_articles = [
        article
        for category in topics_to_fetch
        for article in articles_by_category.get(category, [])
    ]
    if all_articles:
        decode_batch_failed = False
        try:
            decoded_articles = gnewsdecoder([article["link"] for article in all_articles])
        except Exception as e:
            logger.warning("Could not decode Google News URLs in batch: %s", e)
            decoded_articles = []
            decode_batch_failed = True

        if not isinstance(decoded_articles, list):
            logger.warning("Google News decoder returned an unexpected batch response")
            decoded_articles = []
            decode_batch_failed = True

        if len(decoded_articles) == len(all_articles):
            for article, decoded in zip(all_articles, decoded_articles):
                if isinstance(decoded, dict) and decoded.get("success") and decoded.get("decoded_url"):
                    article["url"] = decoded["decoded_url"]
                else:
                    logger.warning(
                        "Could not decode Google News URL %s: %s",
                        article["link"],
                        decoded.get("message", "No decoded URL returned")
                        if isinstance(decoded, dict)
                        else "Invalid decoder result"
                    )
                    article["url"] = article["link"]
        elif not decode_batch_failed:
            logger.warning(
                "Google News decoder returned %d results for %d URLs",
                len(decoded_articles),
                len(all_articles)
            )

        for article in all_articles:
            article.setdefault("url", article["link"])

    for cat in topics_to_fetch:
        final_articles = []
        seen_titles = set()
        for article in articles_by_category.get(cat, []):
            if article["title"] in seen_titles:
                continue
            seen_titles.add(article["title"])

            publisher_info = _lookup_publisher(article["url"])

            final_articles.append({
                "title": article["title"],
                "url": article["url"],
                "snippet": article["snippet"],
                "age": article["pub_date"],
                "publisher": {
                    "name": publisher_info["name"] if publisher_info["name"] != article["url"] else article["source_name"],
                    "bias": publisher_info["bias"],
                    "score": publisher_info["score"]
                }
            })

        results[cat] = final_articles[:6]
        logger.info("Trending '%s': fetched %d articles via Google News RSS", cat, len(results[cat]))

    return {"topics": results}
