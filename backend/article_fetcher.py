# article_fetcher.py
"""
Article URL ingestion and content extraction module for BeyondBinary.
Retrieves and parses web articles from news outlets, extracting headline,
clean body text, and publication metadata for credibility and bias analysis.
"""

import logging
import re
import html as html_lib
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import lxml.html
import requests
from feed_parser import fetch_content_from_rss
from news_provider import get_news_provider
from playwright_fetcher import sync_fetch_with_playwright

try:
    from googlenewsdecoder import gnewsdecoder
    _HAS_GNEWS_DECODER = True
except (ImportError, ModuleNotFoundError):
    _HAS_GNEWS_DECODER = False
    gnewsdecoder = None

logger = logging.getLogger("BeyondBinary.ArticleFetcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BeyondBinary/1.2"
)

def resolve_google_news_url(url: str) -> str:
    """Resolve a Google News article wrapper to its publisher URL."""
    if "news.google.com" not in url:
        return url
    if not _HAS_GNEWS_DECODER or gnewsdecoder is None:
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
        netloc = netloc.split(":")[0]
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

        if len(paragraphs) < 2:
            for p in doc.xpath('//p'):
                raw_p = re.sub(r"\s+", " ", p.text_content().strip())
                if len(raw_p) >= 25 and not any(raw_p.lower().startswith(b) for b in [
                    "subscribe", "sign up", "follow us", "cookie policy",
                    "advertisement", "all rights reserved", "terms of service"
                ]):
                    if raw_p not in paragraphs:
                        paragraphs.append(raw_p)

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

def _query_search_bypass(query: str, original_url: str, original_domain: str, original_title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolves a paywalled or obfuscated news story via Brave Search index."""
    try:
        from search_provider import get_search_provider
        search_prov = get_search_provider()
        if not search_prov.is_configured:
            return None

        # Clean query: strip source prefixes/suffixes if present
        clean_q = query.strip()
        for sep in [" - ", " | "]:
            if sep in clean_q:
                clean_q = clean_q.split(sep)[0].strip()

        logger.info("Attempting Search Bypass for query: '%s'", clean_q)
        search_results = search_prov.search(clean_q, count=4)
        if not search_results:
            return None

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Step A: Try direct fetch on top publisher results (skipping google news links)
        for cand in search_results[:2]:
            cand_url = cand.get("url", "")
            cand_domain = extract_domain(cand_url) or ""
            if not cand_url or "google.com" in cand_domain:
                continue

            try:
                cand_resp = requests.get(cand_url, headers=headers, timeout=2.5, allow_redirects=True)
                if cand_resp.status_code == 200:
                    cand_parse = _parse_html_content(cand_resp.text, cand_resp.url, extract_domain(cand_resp.url) or cand_domain)
                    if cand_parse.get("success") and cand_parse.get("word_count", 0) >= 45:
                        logger.info("Search Bypass directly extracted %d words from publisher: %s", cand_parse["word_count"], cand_url)
                        return cand_parse
            except Exception as e:
                logger.debug("Direct candidate fetch failed for %s: %s", cand_url, e)

        # Step B: Assemble rich indexed search snippets
        top_title = html_lib.unescape(search_results[0].get("title", ""))
        for sep in [" - ", " | "]:
            if sep in top_title:
                top_title = top_title.split(sep)[0].strip()

        extracted_snippets = []
        for sr in search_results:
            snip = html_lib.unescape(sr.get("snippet", "")).strip()
            if snip and len(snip) > 30 and snip not in extracted_snippets:
                extracted_snippets.append(snip)

        combined_body = "\n\n".join(extracted_snippets)
        w_count = len(combined_body.split())
        if w_count >= 20:
            top_url = search_results[0].get("url", original_url)
            top_domain = extract_domain(top_url) or original_domain or "Wire Dispatch"
            logger.info("Search Bypass assembled %d words from %d snippets for '%s'", w_count, len(extracted_snippets), clean_q)
            return {
                "success": True,
                "url": top_url,
                "domain": top_domain,
                "title": top_title or original_title or (top_domain.capitalize() + " Dispatch"),
                "text": combined_body,
                "word_count": w_count,
                "error": None
            }
    except Exception as err:
        logger.warning("Search Bypass error: %s", err)
    return None

def fetch_article_from_url(url: str, title: Optional[str] = None, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Fetches and extracts title and clean text content from a news article URL.
    Handles Google News redirect wrappers and anti-bot firewalls via multi-tier fallback.
    """
    clean_url = (url or "").strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    # Check if Google News wrapper (skip slow gnewsdecoder if headline is provided for direct search bypass)
    if "news.google.com" in clean_url and not title:
        clean_url = resolve_google_news_url(clean_url)

    domain = extract_domain(clean_url) or ""
    is_google_news = "news.google.com" in clean_url

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
        # TIER 0: If Google News wrapper could not be resolved to publisher, bypass to Search Index
        if is_google_news:
            logger.info("Google News link detected (%s). Resolving via Search Bypass with headline: %s", clean_url, title)
            search_query = (title or "").strip()
            if not search_query:
                parsed_u = urlparse(clean_url)
                slug = parsed_u.path.strip("/").split("/")[-1]
                slug_words = re.sub(r"[^a-zA-Z0-9\s]", " ", slug)
                terms = [w for w in slug_words.split() if len(w) > 3][:6]
                if terms:
                    search_query = " ".join(terms)

            if search_query:
                bypass_res = _query_search_bypass(search_query, clean_url, domain, title)
                if bypass_res and bypass_res.get("success"):
                    return bypass_res

        # TIER 1: Direct Request (Skip if it's still a Google News wrapper)
        if not is_google_news:
            logger.info("Fetching article content from URL: %s", clean_url)
            try:
                response = requests.get(clean_url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    parse_res = _parse_html_content(response.text, response.url, extract_domain(response.url) or domain)
                    if parse_res["success"] and parse_res["word_count"] >= 35:
                        return parse_res
                    logger.info("Parse returned sparse text for %s. Trying fallbacks...", response.url)
                else:
                    logger.warning("Tier 1 failed for %s: HTTP %d", clean_url, response.status_code)
            except Exception as e:
                logger.warning("Tier 1 direct GET exception for %s: %s", clean_url, e)

        # TIER 1.5: Playwright Stealth (if installed)
        logger.info("Attempting Tier 1.5 fallback (Playwright Stealth) for %s", clean_url)
        pw_res = sync_fetch_with_playwright(clean_url, timeout)
        if pw_res.get("success") and pw_res.get("html"):
            final_url = pw_res.get("url", clean_url)
            final_domain = extract_domain(final_url) or domain
            pw_parse_res = _parse_html_content(pw_res["html"], final_url, final_domain)
            if pw_parse_res.get("success") and pw_parse_res.get("word_count", 0) >= 35:
                return pw_parse_res

        # TIER 2: Try GNews Aggregator
        logger.info("Attempting Tier 2 fallback (GNews) for %s", clean_url)
        try:
            news_provider = get_news_provider()
            news_res = news_provider.fetch_article_by_url(clean_url)
            if news_res.get("success") and news_res.get("word_count", 0) >= 35:
                return {
                    "success": True,
                    "url": news_res.get("url") or clean_url,
                    "domain": extract_domain(news_res.get("url") or clean_url) or domain,
                    "title": news_res["title"],
                    "text": news_res["text"],
                    "word_count": news_res["word_count"],
                    "error": None
                }
        except Exception as e:
            logger.debug("Tier 2 GNews exception: %s", e)

        # TIER 3: Try RSS Fallback
        logger.info("Attempting Tier 3 fallback (RSS) for %s", clean_url)
        try:
            rss_res = fetch_content_from_rss(clean_url)
            if rss_res.get("success") and rss_res.get("word_count", 0) >= 35:
                return {
                    "success": True,
                    "url": rss_res.get("url") or clean_url,
                    "domain": extract_domain(rss_res.get("url") or clean_url) or domain,
                    "title": rss_res["title"],
                    "text": rss_res["text"],
                    "word_count": rss_res["word_count"],
                    "error": None
                }
        except Exception as e:
            logger.debug("Tier 3 RSS exception: %s", e)

        # TIER 4: Search Index Fallback (WAF / Paywall / Cloudflare / Akamai Bypass)
        logger.info("Attempting Tier 4 fallback (Brave Search Index WAF Bypass) for %s", clean_url)
        search_query = (title or "").strip()
        if not search_query:
            parsed_u = urlparse(clean_url)
            slug = parsed_u.path.strip("/").split("/")[-1]
            slug_words = re.sub(r"[^a-zA-Z0-9\s]", " ", slug)
            terms = [w for w in slug_words.split() if len(w) > 3][:8]
            if terms:
                search_query = " ".join(terms)

        if search_query:
            bypass_res = _query_search_bypass(search_query, clean_url, domain, title)
            if bypass_res and bypass_res.get("success"):
                return bypass_res

        return {
            "success": False,
            "url": clean_url,
            "domain": domain,
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
