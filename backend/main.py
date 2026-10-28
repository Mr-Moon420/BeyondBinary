import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# main.py
"""
FastAPI application for BeyondBinary credibility and media bias analysis.
Exposes endpoints for full article analysis (claims, verification, and bias),
status, health, and trending news feed.
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
try:
    from googlenewsdecoder import gnewsdecoder
    _HAS_GNEWS_DECODER = True
except (ImportError, ModuleNotFoundError):
    _HAS_GNEWS_DECODER = False
    gnewsdecoder = None
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

import re
import time
import html
from lxml import etree, html as lxml_html

# Load AllSides ratings for publisher bias lookup
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ALLSIDES_FILE = os.path.join(_BASE_DIR, "data", "allsides_ratings.json")
_ALLSIDES: Dict[str, Dict[str, Any]] = {}
try:
    with open(_ALLSIDES_FILE, "r", encoding="utf-8") as f:
        _ALLSIDES = json.load(f)
except Exception:
    pass

# Build index for lookup by normalized name
_ALLSIDES_BY_NAME: Dict[str, Dict[str, Any]] = {}
for _dom, _info in _ALLSIDES.items():
    _nm = _info.get("name", "").strip()
    if _nm:
        _clean_nm = re.sub(r"[^a-zA-Z0-9]", "", _nm).lower()
        _ALLSIDES_BY_NAME[_clean_nm] = {**_info, "domain": _dom}


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


def _lookup_publisher(
    url: str,
    source_url: Optional[str] = None,
    source_name: Optional[str] = None
) -> Dict[str, Any]:
    """Look up publisher info and political bias from AllSides with multi-level fallbacks."""
    # 1. Check direct domain from decoded URL or publisher homepage
    for candidate_url in [url, source_url]:
        if not candidate_url:
            continue
        domain = _extract_domain(candidate_url)
        if not domain or "google.com" in domain:
            continue

        if domain in _ALLSIDES:
            info = _ALLSIDES[domain]
            return {
                "domain": domain,
                "name": info.get("name", source_name or domain),
                "bias": info.get("bias", "Unrated"),
                "score": info.get("score", None)
            }
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in _ALLSIDES:
                info = _ALLSIDES[parent]
                return {
                    "domain": domain,
                    "name": info.get("name", source_name or parent),
                    "bias": info.get("bias", "Unrated"),
                    "score": info.get("score", None)
                }

    # 2. Match by publisher source name
    if source_name:
        clean = re.sub(r"[^a-zA-Z0-9]", "", source_name).lower()
        if clean in _ALLSIDES_BY_NAME:
            info = _ALLSIDES_BY_NAME[clean]
            return {
                "domain": info.get("domain", ""),
                "name": info.get("name", source_name),
                "bias": info.get("bias", "Unrated"),
                "score": info.get("score", None)
            }
        for k, info in _ALLSIDES_BY_NAME.items():
            if (len(k) > 3 and k in clean) or (len(clean) > 3 and clean in k):
                return {
                    "domain": info.get("domain", ""),
                    "name": info.get("name", source_name),
                    "bias": info.get("bias", "Unrated"),
                    "score": info.get("score", None)
                }

    clean_name = source_name or _extract_domain(url) or "Syndicated Press"
    return {
        "domain": _extract_domain(url),
        "name": clean_name,
        "bias": "Unrated",
        "score": None
    }

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
    title: Optional[str] = None


class UrlInput(BaseModel):
    url: str
    title: Optional[str] = None


_FRONTEND_DIST = os.path.join(_BASE_DIR, "frontend", "dist")
if os.path.exists(_FRONTEND_DIST) and os.path.exists(os.path.join(_FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

@app.get("/status")
def status():
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

@app.get("/")
def root():
    dist_index = os.path.join(_FRONTEND_DIST, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    return status()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fetch-url")
def fetch_url(data: UrlInput):
    """Fetches clean text and metadata from a news article URL."""
    return fetch_article_from_url(data.url, title=data.title)


@app.post("/analyze")
def analyze(article: ArticleInput):
    input_text = (article.text or "").strip()
    source_url = article.url
    article_title = article.title or ""

    # 1. Auto-detect if input is a URL or if text is omitted with a URL provided
    if is_valid_url(input_text):
        source_url = input_text
        fetch_res = fetch_article_from_url(source_url, title=article.title)
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
        fetch_res = fetch_article_from_url(source_url, title=article.title)
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

    # 5. Composite calibrated credibility scoring
    loaded_density = bias_result.get("framing_analysis", {}).get("density_pct", 0.0)
    credibility_score = compute_score(verified_claims, loaded_density_pct=loaded_density)

    provider = get_search_provider()
    if hasattr(provider, 'brave') and provider.brave.is_configured:
        search_status = "Brave Search API"
    else:
        search_status = "Multi-Tier Live Web & Wikipedia Wire"

    return {
        "title": article_title,
        "source_url": source_url,
        "text": input_text,
        "credibility_score": credibility_score,
        "claims": verified_claims,
        "bias_analysis": bias_result,
        "extractor": "ClaimBuster-DeBERTaV2",
        "search_provider": search_status
    }



# ── Echo Chamber Comparison Endpoint ──────────────────────────────

class CompareRequest(BaseModel):
    url_a: Optional[str] = None
    text_a: Optional[str] = None
    title_a: Optional[str] = None
    source_a: Optional[str] = None

    url_b: Optional[str] = None
    text_b: Optional[str] = None
    title_b: Optional[str] = None
    source_b: Optional[str] = None


def _analyze_outlet_payload(
    url: Optional[str],
    raw_text: Optional[str],
    fallback_title: Optional[str] = None,
    fallback_source: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to extract and analyze a single outlet for comparison."""
    article_title = fallback_title or "Untitled Report"
    input_text = (raw_text or "").strip()
    source_name = fallback_source or ""

    # If domain or source known without URL, synthesize mock URL for AllSides grounding
    if not url and fallback_source:
        clean_nm = re.sub(r"[^a-zA-Z0-9]", "", fallback_source).lower()
        if clean_nm in _ALLSIDES_BY_NAME:
            dom = _ALLSIDES_BY_NAME[clean_nm].get("domain", "")
            if dom:
                url = f"https://{dom}"

    if url and not input_text:
        fetch_res = fetch_article_from_url(url, title=fallback_title)
        if fetch_res.get("success"):
            input_text = fetch_res.get("text", "")
            if fetch_res.get("title"):
                article_title = fetch_res["title"]
        else:
            logger.warning("Failed to fetch outlet URL: %s", url)

    if not source_name and url:
        dom = _extract_domain(url)
        pub_info = _lookup_publisher(dom)
        source_name = pub_info.get("name") or dom

    if not input_text:
        return {
            "title": article_title,
            "source_name": source_name or "Unknown Source",
            "source_url": url or "",
            "credibility_score": 50.0,
            "claims": [],
            "bias_analysis": {
                "bias_label": "Center",
                "spectrum_score": 0.0,
                "confidence": 0.5,
                "stance": {"probabilities": {"Left": 0.33, "Center": 0.34, "Right": 0.33}},
                "loaded_language": {"density_pct": 0.0, "loaded_words": []}
            },
            "error": "Could not extract sufficient text."
        }

    # 1. Claims extraction (top 3 key claims for comparison efficiency)
    claims = extract_claims(input_text)
    verified_claims = [verify_claim(c) for c in claims[:3]]

    # 2. Evidence sources collection
    sources = []
    for c in verified_claims:
        sources.extend(c.get("sources", []))

    # 3. Bias and Framing Analysis
    bias_res = analyze_bias(text=input_text, source_url=url, evidence_sources=sources)
    loaded_density = bias_res.get("loaded_language", {}).get("density_pct", 0.0)

    # 4. Credibility scoring
    cred_score = compute_score(verified_claims, loaded_density_pct=loaded_density)

    # Resolve outlet display name
    dom_rating = bias_res.get("domain_rating") or {}
    resolved_source = source_name or dom_rating.get("name") or "Independent / Wire"

    return {
        "title": article_title,
        "source_name": resolved_source,
        "source_url": url or "",
        "credibility_score": cred_score,
        "claims": verified_claims,
        "bias_analysis": bias_res,
        "word_count": len(input_text.split()),
        "summary": input_text[:350] + "..." if len(input_text) > 350 else input_text
    }


def _compute_echo_chamber_divergence(outlet_a: Dict[str, Any], outlet_b: Dict[str, Any]) -> Dict[str, Any]:
    """Computes polarization and rhetoric divergence metrics between two outlets."""
    bias_a = outlet_a.get("bias_analysis") or {}
    bias_b = outlet_b.get("bias_analysis") or {}

    stance_a = bias_a.get("stance") or {}
    stance_b = bias_b.get("stance") or {}

    probs_a = stance_a.get("probabilities") or {"Left": 0.33, "Center": 0.34, "Right": 0.33}
    probs_b = stance_b.get("probabilities") or {"Left": 0.33, "Center": 0.34, "Right": 0.33}

    # Total Variation Distance on stance distribution (0.0 to 100.0)
    l_diff = abs(probs_a.get("Left", 0) - probs_b.get("Left", 0))
    c_diff = abs(probs_a.get("Center", 0) - probs_b.get("Center", 0))
    r_diff = abs(probs_a.get("Right", 0) - probs_b.get("Right", 0))
    tv_divergence = 0.5 * (l_diff + c_diff + r_diff) * 100.0

    # Domain rating spectrum distance if available (-1.0 to 1.0)
    spectrum_a = bias_a.get("spectrum_score", 0.0)
    spectrum_b = bias_b.get("spectrum_score", 0.0)
    spectrum_delta = abs(spectrum_a - spectrum_b)  # 0.0 to 2.0

    # Composite Polarization Index (blends NLP probability shift + spectrum distance)
    polarization_score = round(min(100.0, max(tv_divergence, (spectrum_delta / 2.0) * 100.0)), 1)

    # Rhetoric & loaded language contrast
    loaded_a = bias_a.get("loaded_language") or {}
    loaded_b = bias_b.get("loaded_language") or {}

    density_a = round(loaded_a.get("density_pct", 0.0), 2)
    density_b = round(loaded_b.get("density_pct", 0.0), 2)
    density_diff = round(abs(density_a - density_b), 2)

    terms_a = loaded_a.get("detected_words", []) or loaded_a.get("loaded_words", [])
    terms_b = loaded_b.get("detected_words", []) or loaded_b.get("loaded_words", [])

    # Categorize divergence level
    if polarization_score >= 55.0:
        divergence_level = "High Polarization (Echo Chamber Divergence)"
        divergence_desc = "Outlets exhibit sharp ideological divergence and opposing framing."
    elif polarization_score >= 25.0:
        divergence_level = "Moderate Divergence (Editorial Framing Variance)"
        divergence_desc = "Outlets share some factual core but emphasize different partisan narratives."
    else:
        divergence_level = "Low Divergence (Consensus Reporting)"
        divergence_desc = "Both outlets exhibit neutral or concordant coverage of this event."

    name_a = outlet_a.get("source_name", "Source A")
    name_b = outlet_b.get("source_name", "Source B")
    label_a = bias_a.get("bias_label", "Center")
    label_b = bias_b.get("bias_label", "Center")

    editorial_synthesis = (
        f"{name_a} frames this story from a {label_a} perspective (sensationalism density: {density_a}%), "
        f"whereas {name_b} reports through a {label_b} lens (sensationalism density: {density_b}%). "
        f"{divergence_desc}"
    )

    return {
        "polarization_score": polarization_score,
        "divergence_level": divergence_level,
        "divergence_description": divergence_desc,
        "stance_divergence_pct": round(tv_divergence, 1),
        "spectrum_delta": round(spectrum_delta, 2),
        "rhetoric_contrast": {
            "density_a": density_a,
            "density_b": density_b,
            "density_diff": density_diff,
            "terms_a": list(set(terms_a))[:8],
            "terms_b": list(set(terms_b))[:8],
            "higher_sensationalism": name_a if density_a > density_b else (name_b if density_b > density_a else "Equal")
        },
        "editorial_synthesis": editorial_synthesis
    }


@app.post("/compare")
async def compare_perspectives(request: CompareRequest):
    """
    Side-by-Side Echo Chamber Comparison Endpoint.
    Analyzes two perspectives of the same story and calculates
    ideological divergence, rhetoric disparity, and factual overlap.
    """
    outlet_a = _analyze_outlet_payload(
        url=request.url_a,
        raw_text=request.text_a,
        fallback_title=request.title_a,
        fallback_source=request.source_a
    )
    outlet_b = _analyze_outlet_payload(
        url=request.url_b,
        raw_text=request.text_b,
        fallback_title=request.title_b,
        fallback_source=request.source_b
    )

    divergence = _compute_echo_chamber_divergence(outlet_a, outlet_b)

    return {
        "outlet_a": outlet_a,
        "outlet_b": outlet_b,
        "comparison": divergence
    }


# ── Trending News Feed ──────────────────────────────────────────────

# Real-time Google News feeds (24h search feeds ensure constantly updated live breaking stories)
TOPIC_FEEDS = {
    "politics": "https://news.google.com/rss/search?q=politics+when:24h&hl=en-US&gl=US&ceid=US:en",
    "tech": "https://news.google.com/rss/search?q=technology+OR+AI+when:24h&hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/search?q=business+OR+economy+OR+markets+when:24h&hl=en-US&gl=US&ceid=US:en",
    "world": "https://news.google.com/rss/search?q=world+news+when:24h&hl=en-US&gl=US&ceid=US:en",
    "sports": "https://news.google.com/rss/search?q=sports+when:24h&hl=en-US&gl=US&ceid=US:en",
}

TOPIC_FALLBACK_FEEDS = {
    "politics": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=en-US&gl=US&ceid=US:en",
    "tech": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "world": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
    "sports": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
}

# In-memory cache for fast responsive delivery
_DECODED_URL_CACHE: Dict[str, str] = {}
_TRENDING_FEED_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_FEED_CACHE_TTL_SECONDS = 180  # 3 minutes cache TTL for high freshness


@app.get("/trending")
def trending(topic: Optional[str] = None, refresh: bool = False):
    """
    Fetches real-time trending news headlines via direct Google News topic feeds,
    parses cross-source reporting coverage, and resolves original publisher URLs.
    Supports query params:
      - ?topic=politics|tech|business|world|sports
      - ?refresh=true (forces cache invalidation and immediate live pull)
    """
    import requests as req
    import email.utils

    requested_topic = (topic or "politics").lower().strip()
    if requested_topic in TOPIC_FEEDS:
        topics_to_fetch = [requested_topic]
    else:
        topics_to_fetch = ["politics"]

    now = time.time()
    results: Dict[str, List[Dict[str, Any]]] = {}

    for cat in topics_to_fetch:
        # 1. Check in-memory cache if not explicitly refreshing
        if not refresh and cat in _TRENDING_FEED_CACHE:
            cached_time, cached_articles = _TRENDING_FEED_CACHE[cat]
            if now - cached_time < _FEED_CACHE_TTL_SECONDS:
                results[cat] = cached_articles
                logger.info("Served '%s' wire from memory cache (%d articles)", cat, len(cached_articles))
                continue

        feed_url = TOPIC_FEEDS.get(cat)
        fallback_url = TOPIC_FALLBACK_FEEDS.get(cat)
        if not feed_url:
            results[cat] = []
            continue

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BeyondBinary/1.2"
            }
            resp = req.get(feed_url, headers=headers, timeout=8.0)
            if resp.status_code != 200 and fallback_url:
                logger.warning("Primary feed failed for '%s' (HTTP %d), trying fallback...", cat, resp.status_code)
                resp = req.get(fallback_url, headers=headers, timeout=8.0)

            if resp.status_code != 200:
                logger.warning("Google News feed fetch failed for '%s': HTTP %d", cat, resp.status_code)
                results[cat] = []
                continue

            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(resp.content, parser=parser)
            items = root.xpath('//item')

            raw_articles = []
            seen_titles = set()

            for item in items:
                def get_text(tag: str) -> str:
                    r = item.xpath(f'./{tag}/text()')
                    return r[0].strip() if r else ""

                title_raw = get_text('title')
                link = get_text('link')
                pub_date = get_text('pubDate')
                raw_desc = get_text('description')

                if not title_raw or not link:
                    continue

                # Google News adds " - Outlet Name"
                article_title = title_raw
                source_name = ""
                source_url = ""

                source_tags = item.xpath('./source')
                if source_tags:
                    source_name = (source_tags[0].text or "").strip()
                    source_url = source_tags[0].attrib.get('url', '').strip()

                if " - " in title_raw:
                    parts = title_raw.rsplit(" - ", 1)
                    article_title = parts[0].strip()
                    if not source_name:
                        source_name = parts[1].strip()

                if article_title.lower() in seen_titles:
                    continue
                seen_titles.add(article_title.lower())

                # Parse multi-outlet coverage perspectives from RSS description
                perspectives: List[Dict[str, Any]] = []
                if raw_desc:
                    try:
                        tree = lxml_html.fragment_fromstring(raw_desc, create_parent='div')
                        lis = tree.xpath('.//li')
                        for li in lis:
                            a_tags = li.xpath('.//a')
                            font_tags = li.xpath('.//font')
                            p_title = a_tags[0].text_content().strip() if a_tags else ''
                            p_source = font_tags[0].text_content().strip() if font_tags else ''
                            p_link = a_tags[0].attrib.get('href', '') if a_tags else ''
                            if p_title:
                                p_bias_info = _lookup_publisher(p_link, None, p_source)
                                perspectives.append({
                                    "title": p_title,
                                    "source": p_source,
                                    "url": p_link,
                                    "bias": p_bias_info.get("bias", "Unrated")
                                })
                    except Exception:
                        pass

                # Build clean editorial excerpt
                if len(perspectives) > 1:
                    other_outlets = [p['source'] for p in perspectives[1:] if p.get('source')]
                    unique_outlets = list(dict.fromkeys(other_outlets))
                    if unique_outlets:
                        clean_snippet = f"Syndicated reporting tracked across {len(perspectives)} wire outlets, including {', '.join(unique_outlets[:3])}."
                    else:
                        clean_snippet = f"Breaking syndicated coverage tracked across {len(perspectives)} press desks."
                else:
                    stripped = re.sub(r'<[^>]+>', ' ', raw_desc)
                    stripped = html.unescape(stripped)
                    stripped = re.sub(r'\s+', ' ', stripped).strip()
                    stripped = re.sub(r'See more headlines.*$', '', stripped, flags=re.IGNORECASE).strip()
                    if stripped.startswith(article_title):
                        stripped = stripped[len(article_title):].strip()
                    if source_name and stripped.endswith(source_name):
                        stripped = stripped[:-len(source_name)].strip()

                    if stripped and len(stripped) > 20 and stripped != article_title:
                        clean_snippet = stripped
                    else:
                        clean_snippet = f"Live dispatch filed by {source_name or 'editorial wire'}. Verification & cross-source claim analysis ready."

                raw_articles.append({
                    "title": article_title,
                    "link": link,
                    "pub_date": pub_date,
                    "source_name": source_name,
                    "source_url": source_url,
                    "snippet": clean_snippet,
                    "perspectives": perspectives[1:4]
                })

                if len(raw_articles) >= 50:
                    break

            # Sort articles chronologically descending so newest breaking stories are first
            def _parse_timestamp(d_str: str) -> float:
                try:
                    return email.utils.parsedate_to_datetime(d_str).timestamp()
                except Exception:
                    return 0.0

            raw_articles.sort(key=lambda a: _parse_timestamp(a["pub_date"]), reverse=True)
            raw_articles = raw_articles[:25]

            # Batch decode uncached URLs
            uncached_links = [
                a["link"] for a in raw_articles
                if a["link"] not in _DECODED_URL_CACHE
            ]

            if uncached_links and _HAS_GNEWS_DECODER and gnewsdecoder:
                try:
                    decoded_res = gnewsdecoder(uncached_links)
                    if isinstance(decoded_res, list) and len(decoded_res) == len(uncached_links):
                        for original_link, d in zip(uncached_links, decoded_res):
                            if isinstance(d, dict) and d.get("success") and d.get("decoded_url"):
                                _DECODED_URL_CACHE[original_link] = d["decoded_url"]
                            else:
                                _DECODED_URL_CACHE[original_link] = original_link
                    elif isinstance(decoded_res, dict) and len(uncached_links) == 1:
                        if decoded_res.get("success") and decoded_res.get("decoded_url"):
                            _DECODED_URL_CACHE[uncached_links[0]] = decoded_res["decoded_url"]
                except Exception as dec_err:
                    logger.warning("Batch Google News decoding failed: %s", dec_err)

            final_articles: List[Dict[str, Any]] = []
            for art in raw_articles:
                resolved_url = _DECODED_URL_CACHE.get(art["link"], art["link"])
                pub_info = _lookup_publisher(resolved_url, art["source_url"], art["source_name"])
                final_articles.append({
                    "title": art["title"],
                    "url": resolved_url,
                    "snippet": art["snippet"],
                    "age": art["pub_date"],
                    "publisher": pub_info,
                    "perspectives": art["perspectives"]
                })

            _TRENDING_FEED_CACHE[cat] = (now, final_articles)
            results[cat] = final_articles
            logger.info("Trending '%s': successfully refreshed %d articles", cat, len(final_articles))

        except Exception as e:
            logger.error("Trending fetch error for '%s': %s", cat, e)
            results[cat] = []

    return {"topics": results}
