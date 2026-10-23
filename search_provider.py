# search_provider.py
"""
Search provider module for BeyondBinary.
Integrates with the Brave Search API to retrieve real-time, authoritative
web evidence for factual claim verification.
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
import requests
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger("BeyondBinary.Search")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class BraveSearchProvider:
    """
    Search client for Brave Search API (https://brave.com/search/api/).
    Provides web snippets, page titles, URLs, and extra context to verify claims.
    """

    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 6.0):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY", "").strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key)

    def clean_query(self, claim: str) -> str:
        """
        Cleans and optimizes a factual claim for search querying.
        Removes leading/trailing quotes, excessive punctuation, and common attribution prefixes.
        """
        query = claim.strip().strip('"\'`')
        # Remove common reporting prefixes that detract from factual matching
        attribution_patterns = [
            r"^(it is reported that|sources say that|according to reports,?\s*|breaking news:?\s*|reports indicate that\s*)",
            r"^(claims have emerged that\s*|unconfirmed reports suggest that\s*)"
        ]
        for pat in attribution_patterns:
            query = re.sub(pat, "", query, flags=re.IGNORECASE).strip()

        # Remove trailing period or semicolon
        query = query.rstrip(". ;")
        return query

    def search(self, query: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        Executes a search query against the Brave Web Search API.

        Returns a list of result dictionaries containing:
        - title: Web page title
        - url: Source URL
        - snippet: Main description snippet
        - extra_snippets: Any additional context snippets
        - evidence_text: Combined clean text formatted for NLI premise
        """
        if not self.is_configured:
            logger.warning("BraveSearch: BRAVE_API_KEY is not configured in .env or environment.")
            return []

        cleaned_query = self.clean_query(query)
        if not cleaned_query:
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
            "User-Agent": "BeyondBinary/1.0 (Media Credibility Analyzer; contact@beyondbinary.local)"
        }

        params = {
            "q": cleaned_query,
            "count": min(max(count, 1), 10),
            "search_lang": "en",
            "text_decorations": False,  # Clean plain text without <b> or <strong> tags
            "result_filter": "web"
        }

        try:
            logger.info("Querying Brave Search for claim: '%s'", cleaned_query[:80])
            response = requests.get(
                self.ENDPOINT,
                headers=headers,
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 401:
                logger.error("BraveSearch: 401 Unauthorized - The provided BRAVE_API_KEY is invalid.")
                return []
            elif response.status_code == 429:
                logger.warning("BraveSearch: 429 Rate Limit Exceeded - Check your Brave Search monthly quota.")
                return []
            elif response.status_code != 200:
                logger.error("BraveSearch HTTP Error %s: %s", response.status_code, response.text[:200])
                return []

            data = response.json()
            raw_results = data.get("web", {}).get("results", [])
            
            parsed_results = []
            for item in raw_results:
                title = item.get("title", "").strip()
                url = item.get("url", "").strip()
                description = item.get("description", "").strip()
                extra = item.get("extra_snippets") or []
                
                # Filter out empty or low-substance results
                if not description and not extra:
                    continue

                # Build coherent evidence text for NLI
                snippets_combined = description
                if extra and len(extra) > 0:
                    snippets_combined += " " + " ".join(extra[:2])
                
                evidence_text = f"{title}. {snippets_combined}" if title else snippets_combined

                parsed_results.append({
                    "title": title,
                    "url": url,
                    "snippet": description,
                    "extra_snippets": extra,
                    "evidence_text": evidence_text
                })

            logger.info("BraveSearch returned %d relevant results", len(parsed_results))
            return parsed_results

        except requests.exceptions.Timeout:
            logger.warning("BraveSearch request timed out after %.1f seconds.", self.timeout)
            return []
        except requests.exceptions.RequestException as e:
            logger.error("BraveSearch network error: %s", e)
            return []
        except Exception as e:
            logger.error("BraveSearch unexpected error: %s", e)
            return []


# Default singleton instance
_default_provider: Optional[BraveSearchProvider] = None

def get_search_provider() -> BraveSearchProvider:
    """Returns or initializes the default BraveSearchProvider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = BraveSearchProvider()
    return _default_provider


def fetch_web_evidence(claim: str, max_results: int = 3) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Convenience function to fetch evidence for a claim using Brave Search.
    
    Returns:
    - evidence_texts: list of string evidence passages (suitable for NLI premise input)
    - sources: list of source metadata dictionaries (title, url, snippet)
    """
    provider = get_search_provider()
    results = provider.search(claim, count=max_results)

    evidence_texts = [r["evidence_text"] for r in results if r.get("evidence_text")]
    return evidence_texts, results
