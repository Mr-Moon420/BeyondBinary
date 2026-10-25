# news_provider.py
"""
News aggregator module for BeyondBinary.
Integrates with GNews API to retrieve article content and summaries
when direct fetching fails.
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("BeyondBinary.NewsProvider")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class GNewsProvider:
    """
    Client for GNews API (https://gnews.io/).
    Provides a reliable way to get article summaries and content for current news.
    """

    ENDPOINT = "https://gnews.io/api/v4/articles"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GNEWS_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch_article_by_url(self, url: str) -> Dict[str, Any]:
        """
        Attempts to find the article content via GNews.
        Since GNews doesn't have a direct 'fetch by URL' endpoint,
        we search for the exact URL or title to find the indexed version.
        """
        if not self.is_configured:
            logger.warning("GNewsProvider: GNEWS_API_KEY not configured.")
            return {"success": False, "error": "API key not configured"}

        try:
            # We search for the URL directly in the query.
            # GNews often indexes articles by their exact URL.
            params = {
                "q": f'"{url}"',
                "token": self.api_key,
                "lang": "en",
                "max": 1
            }

            response = requests.get(self.ENDPOINT, params=params, timeout=10.0)

            if response.status_code != 200:
                return {"success": False, "error": f"GNews API returned HTTP {response.status_code}"}

            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                # Fallback: try searching for the domain and a snippet of the URL
                # or just return failure if not found exactly.
                return {"success": False, "error": "Article not found in GNews index."}

            article = articles[0]

            # GNews provides 'content' (a summary/snippet) and 'description'.
            # We combine them to get as much text as possible.
            text = article.get("content", "").strip()
            description = article.get("description", "").strip()

            full_text = f"{description}\n\n{text}".strip()

            if not full_text:
                return {"success": False, "error": "GNews found the article but no content was available."}

            return {
                "success": True,
                "title": article.get("title", ""),
                "text": full_text,
                "word_count": len(full_text.split()),
                "error": None
            }

        except Exception as e:
            logger.error("GNews fetch error: %s", e)
            return {"success": False, "error": str(e)}

# Singleton instance
_default_provider: Optional[GNewsProvider] = None

def get_news_provider() -> GNewsProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = GNewsProvider()
    return _default_provider
