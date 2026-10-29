# feedParsing.py
"""
RSS feed parsing module for BeyondBinary.
Provides a fallback mechanism to extract article content from RSS feeds
when direct web page fetching fails.
"""

import logging
import requests
import lxml.html
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
from article_identity import same_article_url
from public_http import public_get, public_head

logger = logging.getLogger("BeyondBinary.FeedParsing")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BeyondBinary/1.1"
)

def find_rss_feed_url(page_url: str) -> Optional[str]:
    """
    Attempts to discover an RSS feed URL from a given page.
    Checks for common paths and <link> tags in the HTML.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        response = public_get(page_url, headers=headers, timeout=5.0)
        if response.status_code != 200:
            return None

        doc = lxml.html.fromstring(response.content)

        # 1. Look for <link rel="alternate" type="application/rss+xml">
        rss_links = doc.xpath('//link[@rel="alternate" and @type="application/rss+xml"]/@href')
        if rss_links:
            return urljoin(page_url, rss_links[0])

        # 2. Look for <link rel="alternate" type="application/atom+xml">
        atom_links = doc.xpath('//link[@rel="alternate" and @type="application/atom+xml"]/@href')
        if atom_links:
            return urljoin(page_url, atom_links[0])

        # 3. Try common feed paths
        common_paths = ["/rss", "/feed", "/index.xml", "/rss.xml", "/feed.xml"]
        parsed = urlparse(page_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        for path in common_paths:
            test_url = urljoin(base_url, path)
            try:
                # Use HEAD request to check existence without downloading body
                head = public_head(test_url, headers=headers, timeout=3.0, allow_redirects=True)
                if head.status_code == 200 and ("xml" in head.headers.get("Content-Type", "").lower()):
                    return test_url
            except Exception:
                continue

    except Exception as e:
        logger.warning("Error discovering RSS feed for %s: %s", page_url, e)

    return None

def fetch_content_from_rss(article_url: str) -> Dict[str, Any]:
    """
    Tries to find the RSS feed for the article's domain and extract the
    content/description for that specific article.
    """
    try:
        # Determine the domain to look for the feed
        parsed = urlparse(article_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        feed_url = find_rss_feed_url(base_url)
        if not feed_url:
            return {"success": False, "error": "Could not discover an RSS feed for this domain."}

        logger.info("Attempting fallback fetch via RSS feed: %s", feed_url)
        headers = {"User-Agent": USER_AGENT}
        response = public_get(feed_url, headers=headers, timeout=10.0)

        if response.status_code != 200:
            return {"success": False, "error": f"RSS feed returned HTTP {response.status_code}"}

        doc = lxml.html.fromstring(response.content)

        # RSS feeds usually have <item> or <entry> tags
        items = doc.xpath('//item') or doc.xpath('//entry')

        for item in items:
            # Find the link to the article
            link = item.xpath('./link/text()') or item.xpath('./link/@href')
            if link and same_article_url(link[0].strip(), article_url):
                # Extract Title
                title = item.xpath('./title/text()')
                title_text = title[0].strip() if title else "No Title"

                # Extract Content/Description
                # RSS uses <description>, Atom uses <summary> or <content>
                content = item.xpath('./description/text()') or \
                          item.xpath('./content/text()') or \
                          item.xpath('./summary/text()')

                if content:
                    full_text = content[0].strip()
                    # Clean HTML tags from the RSS content if present
                    if "<" in full_text and ">" in full_text:
                        full_text = lxml.html.fromstring(full_text).text_content().strip()

                    return {
                        "success": True,
                        "title": title_text,
                        "text": full_text,
                        "word_count": len(full_text.split()),
                        "error": None
                    }

        return {"success": False, "error": "Article not found in the RSS feed."}

    except Exception as e:
        logger.error("Error during RSS fallback fetch: %s", e)
        return {"success": False, "error": str(e)}
