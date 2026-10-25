# article_fetcher.py
"""
Article URL ingestion and content extraction module for BeyondBinary.
Retrieves and parses web articles from news outlets, extracting headline,
clean body text, and publication metadata for credibility and bias analysis.
"""

import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import lxml.html
import requests
from feedParsing import fetch_content_from_rss
from news_provider import get_news_provider
from playwright_fetcher import sync_fetch_with_playwright
from googlenewsdecoder import gnewsdecoder

def resolve_google_news_url(url: str) -> str:
    """Resolve a Google News article wrapper to its publisher URL."""
    if "news.google.com" not in url:
        return url

    try:
        res = gnewsdecoder(url)
        decoded_url = ""
        if isinstance(res, dict):
            if res.get("success") and res.get("decoded_url"):
                decoded_url = res["decoded_url"]
        elif isinstance(res, str):
            decoded_url = res

        if decoded_url and "news.google.com" not in urlparse(decoded_url).netloc:
            return decoded_url

        logger.warning("Google News URL could not be resolved: %s", url)
    except Exception as e:
        logger.warning("Google News URL resolution failed: %s", e)

    return url

logger = logging.getLogger("BeyondBinary.ArticleFetcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BeyondBinary/1.1"
)

def extract_domain(url: str) -> Optional[str]:
    """Extracts clean base domain (e.g. 'cnn.com') from a URL."""
    if not url:
        return None
    url_clean = url.strip().lower()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean
    try:
        parsed = urlparse(url_clean)
        netloc = parsed.netloc or parsed.path
        netloc = netloc.split(":")[0]  # strip port
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None

def is_valid_url(text: str) -> bool:
    """Checks if a string is a valid HTTP/HTTPS URL."""
    if not text:
        return False
    t = text.strip()
    return bool(re.match(r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$", t, flags=re.IGNORECASE))

def _parse_html_content(html_content: str, url: str, domain: str) -> Dict[str, Any]:
    """
    Helper function to apply the core parsing logic to a string of HTML.
    """
    if not html_content or len(html_content.strip()) < 100:
        return {
            "success": False,
            "url": url,
            "domain": domain,
            "title": "",
            "text": "",
            "word_count": 0,
            "error": "Empty or incomplete response received from article URL."
        }

    try:
        doc = lxml.html.fromstring(html_content)

        # 1. Extract Title
        title = ""
        og_title = doc.xpath('//meta[@property="og:title"]/@content')
        if og_title and og_title[0].strip():
            title = og_title[0].strip()
        else:
            tw_title = doc.xpath('//meta[@name="twitter:title"]/@content')
            if tw_title and tw_title[0].strip():
                title = tw_title[0].strip()
            else:
                title_tag = doc.findtext('.//title')
                if title_tag and title_tag.strip():
                    title = title_tag.strip()
                else:
                    h1 = doc.xpath('//h1/text()')
                    if h1 and h1[0].strip():
                        title = h1[0].strip()

        if " - " in title:
            title = title.split(" - ")[0].strip()
        elif " | " in title:
            title = title.split(" | ")[0].strip()

        # 2. Remove noise elements
        noise_tags = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "iframe", "svg"]
        for tag in noise_tags:
            for elem in doc.xpath(f"//{tag}"):
                elem.drop_tree()

        # 3. Extract text paragraphs
        # Search for article tags that actually contain paragraph content
        article_candidates = doc.xpath('//article[.//p] | //div[contains(@class, "article") or contains(@class, "story") or contains(@class, "body")][.//p]')
        search_root = article_candidates[0] if article_candidates else doc

        paragraphs = []
        for p in search_root.xpath('.//p'):
            p_text = p.text_content().strip()
            p_text = re.sub(r"\s+", " ", p_text)
            if len(p_text) < 25:
                continue
            if any(p_text.lower().startswith(b) for b in [
                "subscribe", "sign up", "follow us", "cookie policy",
                "advertisement", "all rights reserved", "terms of service"
            ]):
                continue
            paragraphs.append(p_text)

        # Fallback to searching all paragraphs across doc if candidate was sparse
        if len(paragraphs) < 2:
            for p in doc.xpath('//p'):
                p_text = re.sub(r"\s+", " ", p.text_content().strip())
                if len(p_text) >= 25 and not any(p_text.lower().startswith(b) for b in [
                    "subscribe", "sign up", "follow us", "cookie policy",
                    "advertisement", "all rights reserved", "terms of service"
                ]):
                    if p_text not in paragraphs:
                        paragraphs.append(p_text)

        full_text = "\n\n".join(paragraphs)
        word_count = len(full_text.split())

        if word_count < 25:
            body_text = doc.text_content().strip()
            body_text = re.sub(r"\n{3,}", "\n\n", body_text)
            clean_lines = [line.strip() for line in body_text.split("\n") if len(line.strip()) > 40]
            full_text = "\n\n".join(clean_lines[:15])
            word_count = len(full_text.split())

        if word_count < 15:
            return {
                "success": False,
                "url": url,
                "domain": domain,
                "title": title,
                "text": "",
                "word_count": 0,
                "error": "Could not extract sufficient article text."
            }

        return {
            "success": True,
            "url": url,
            "domain": domain,
            "title": title,
            "text": full_text,
            "word_count": word_count,
            "error": None
        }
    except Exception as e:
        logger.error("Parsing error in _parse_html_content: %s", e)
        return {"success": False, "url": url, "domain": domain, "title": "", "text": "", "word_count": 0, "error": str(e)}

def fetch_article_from_url(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Fetches and extracts title and clean text content from a news article URL.
    Handles Google News redirect wrappers by prioritizing browser-based resolution.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    # Optimization: If it's a Google News redirect link, skip Tier 1 (requests)
    # and go straight to Playwright to resolve the client-side redirect.
    if "news.google.com/rss/articles/" in clean_url:
        clean_url = resolve_google_news_url(clean_url)

    domain = extract_domain(clean_url) or ""
    is_google_news = "news.google.com/rss/articles/" in clean_url

    domain = extract_domain(clean_url) or ""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        # TIER 1: Direct Request (Skip if it's a known wrapper like Google News)
        if not is_google_news:
            logger.info("Fetching article content from URL: %s", clean_url)
            response = requests.get(clean_url, headers=headers, timeout=timeout, allow_redirects=True)

            if response.status_code == 200:
                html_content = response.text
                parse_res = _parse_html_content(html_content, response.url, extract_domain(response.url) or domain)
                if parse_res["success"]:
                    return parse_res

                # If status was 200 but parsing failed, it might be a wrapper page.
                # Fall through to Tiers 1.5+
                logger.info("Parse failed for %s (possible wrapper). Trying fallbacks...", response.url)
            else:
                logger.warning("Tier 1 failed for %s: HTTP %d", clean_url, response.status_code)

        # TIER 1.5: Playwright Stealth (Crucial for Google News redirects)
        logger.info("Attempting Tier 1.5 fallback (Playwright Stealth) for %s", clean_url)
        pw_res = sync_fetch_with_playwright(clean_url, timeout)
        if pw_res["success"]:
            # Use the final URL resolved by Playwright
            final_url = pw_res.get("url", clean_url)
            final_domain = extract_domain(final_url) or domain
            return _parse_html_content(pw_res["html"], final_url, final_domain)

        # TIER 2: Try GNews Aggregator
        logger.info("Attempting Tier 2 fallback (GNews) for %s", clean_url)
        news_provider = get_news_provider()
        news_res = news_provider.fetch_article_by_url(clean_url)
        if news_res["success"]:
            return {
                "success": True,
                "url": news_res.get("url") or clean_url,
                "domain": extract_domain(news_res.get("url") or clean_url) or domain,
                "title": news_res["title"],
                "text": news_res["text"],
                "word_count": news_res["word_count"],
                "error": None
            }

        # TIER 3: Try RSS Fallback
        logger.info("Attempting Tier 3 fallback (RSS) for %s", clean_url)
        rss_res = fetch_content_from_rss(clean_url)
        if rss_res["success"]:
            return {
                "success": True,
                "url": rss_res.get("url") or clean_url,
                "domain": extract_domain(rss_res.get("url") or clean_url) or domain,
                "title": rss_res["title"],
                "text": rss_res["text"],
                "word_count": rss_res["word_count"],
                "error": None
            }

        return {
            "success": False,
            "url": rss_res.get("url") or clean_url,
            "domain": extract_domain(rss_res.get("url") or clean_url) or domain,
            "title": "",
            "text": "",
            "word_count": 0,
            "error": "Unable to load article content after all attempts."
        }

    except requests.exceptions.Timeout:
        logger.warning("Timeout while fetching article URL: %s", clean_url)
        return {"success": False, "url": clean_url, "domain": domain, "title": "", "text": "", "word_count": 0, "error": "Connection timed out."}
    except Exception as e:
        logger.error("Exception while fetching article URL %s: %s", clean_url, e)
        return {"success": False, "url": clean_url, "domain": domain, "title": "", "text": "", "word_count": 0, "error": f"Failed to fetch: {str(e)}"}
