# search_provider.py
"""
Multi-Tier Search Provider module for BeyondBinary.
Provides robust, multi-source evidence retrieval:
1. Brave Search API (if BRAVE_API_KEY is configured)
2. Wikipedia REST API (fast, free, encyclopedic factual evidence)
3. Google News RSS Search (breaking live events & wire coverage)
"""

import os
import re
import json
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("BeyondBinary.Search")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def clean_query(claim: str) -> str:
    """
    Cleans and optimizes a factual claim for search querying.
    Strips rhetorical padding, attribution prefixes, and excessive punctuation.
    """
    query = claim.strip().strip("'\"`")
    attribution_patterns = [
        r"^(it is reported that|sources say that|according to reports,?\s*|breaking news:?\s*|reports indicate that\s*)",
        r"^(claims have emerged that\s*|unconfirmed reports suggest that\s*|officials noted that\s*)",
        r"^(data shows that\s*|studies show that\s*|critics argue that\s*)"
    ]
    for pat in attribution_patterns:
        query = re.sub(pat, "", query, flags=re.IGNORECASE).strip()

    query = query.rstrip(". ;")
    return query


class BraveSearchProvider:
    """Client for Brave Search API."""
    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 5.0):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY", "").strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, count: int = 3) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []

        cleaned_query = clean_query(query)
        if not cleaned_query:
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
            "User-Agent": "BeyondBinary/1.0 (Media Credibility Analyzer)"
        }
        params = {
            "q": cleaned_query,
            "count": min(max(count, 1), 5),
            "search_lang": "en",
            "text_decorations": False,
            "result_filter": "web"
        }

        try:
            logger.info("Querying Brave Search for: '%s'", cleaned_query[:60])
            response = requests.get(self.ENDPOINT, headers=headers, params=params, timeout=self.timeout)
            if response.status_code != 200:
                logger.warning("BraveSearch error HTTP %s", response.status_code)
                return []

            data = response.json()
            raw_results = data.get("web", {}).get("results", [])
            parsed = []
            for item in raw_results:
                title = item.get("title", "").strip()
                url = item.get("url", "").strip()
                desc = item.get("description", "").strip()
                extra = item.get("extra_snippets") or []
                if not desc and not extra:
                    continue
                combined = desc
                if extra:
                    combined += " " + " ".join(extra[:2])
                evidence = f"{title}. {combined}" if title else combined
                parsed.append({
                    "title": title,
                    "url": url,
                    "snippet": desc,
                    "extra_snippets": extra,
                    "evidence_text": evidence,
                    "source_type": "Brave Web Search"
                })
            return parsed
        except Exception as e:
            logger.warning("BraveSearch query failed: %s", e)
            return []


class WikipediaSearchProvider:
    """Free, high-speed encyclopedic retrieval via Wikipedia Search API."""
    def search(self, query: str, count: int = 3) -> List[Dict[str, Any]]:
        cleaned_query = clean_query(query)
        if not cleaned_query:
            return []

        # Remove special quotes
        cleaned_query = re.sub(r'["\x27]', '', cleaned_query).strip()
        encoded = urllib.parse.quote(cleaned_query)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&utf8=&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "BeyondBinary-Verifier/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            raw_items = data.get("query", {}).get("search", [])
            # Prioritize results that match any target year present in the query
            years = re.findall(r'\b(19\d\d|20\d\d)\b', query)
            if years:
                target_year = years[0]
                raw_items.sort(key=lambda it: 0 if target_year in it.get("title", "") or target_year in it.get("snippet", "") else 1)

            items = raw_items[:count]
            results = []
            for it in items:
                title = it.get("title", "")
                raw_snip = it.get("snippet", "")
                clean_snip = re.sub(r"<[^>]+>", "", raw_snip).strip()
                if not clean_snip or len(clean_snip) < 20:
                    continue
                wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({
                    "title": f"Wikipedia: {title}",
                    "url": wiki_url,
                    "snippet": clean_snip,
                    "evidence_text": f"{title}: {clean_snip}",
                    "source_type": "Wikipedia Knowledge Base"
                })
            return results
        except Exception as e:
            logger.warning("WikipediaSearch failed: %s", e)
            return []


class GoogleNewsWireProvider:
    """Free breaking news search via Google News RSS Search."""
    def search(self, query: str, count: int = 3) -> List[Dict[str, Any]]:
        cleaned_query = clean_query(query)
        if not cleaned_query:
            return []

        cleaned_query = re.sub(r'["\x27]', '', cleaned_query).strip()
        encoded = urllib.parse.quote(cleaned_query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            results = []
            for item in root.findall(".//item")[:count]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                source = item.findtext("source", "").strip()
                if not title:
                    continue
                snippet_text = f"Reported by {source}: {title}" if source else title
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet_text,
                    "evidence_text": title,
                    "source_type": f"News Wire ({source})" if source else "News Wire"
                })
            return results
        except Exception as e:
            logger.warning("GoogleNewsWire search failed: %s", e)
            return []


class MultiTierSearchProvider:
    """
    Unified search provider that cascades through available evidence channels:
    1. Brave Search (if API key available)
    2. Wikipedia Knowledge Base
    3. Google News Real-time Wire
    """
    def __init__(self):
        self.brave = BraveSearchProvider()
        self.wiki = WikipediaSearchProvider()
        self.gnews = GoogleNewsWireProvider()

    @property
    def is_configured(self) -> bool:
        # Always True because Wikipedia + Google News free tiers are always available
        return True

    def search(self, query: str, count: int = 3) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        # 1. Try Brave if user configured API key
        if self.brave.is_configured:
            results = self.brave.search(query, count=count)
            if results:
                return results

        # 2. Try Wikipedia Knowledge Base (excellent for facts, history, biographies, entities)
        wiki_results = self.wiki.search(query, count=count)
        if wiki_results:
            results.extend(wiki_results)

        # 3. If needed, supplement with Google News Wire
        if len(results) < count:
            gnews_results = self.gnews.search(query, count=count - len(results))
            if gnews_results:
                results.extend(gnews_results)

        return results[:count]


_default_provider = MultiTierSearchProvider()

def get_search_provider() -> MultiTierSearchProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = MultiTierSearchProvider()
    return _default_provider


def fetch_web_evidence(claim: str, max_results: int = 3) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Convenience function returning:
    - evidence_texts: string passages for NLI Premise input
    - sources: metadata list (title, url, snippet, source_type)
    """
    provider = get_search_provider()
    results = provider.search(claim, count=max_results)
    evidence_texts = [r["evidence_text"] for r in results if r.get("evidence_text")]
    return evidence_texts, results
