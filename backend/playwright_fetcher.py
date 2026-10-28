# playwright_fetcher.py
"""
Advanced article fetching using Playwright with stealth plugins.
Bypasses bot detection by simulating a real browser environment.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except (ImportError, ModuleNotFoundError):
    _HAS_PLAYWRIGHT = False
    async_playwright = None

try:
    from playwright_stealth import Stealth
    _HAS_STEALTH = True
except Exception:
    _HAS_STEALTH = False

logger = logging.getLogger("BeyondBinary.PlaywrightFetcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

async def fetch_with_playwright(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    Fetches page content using a headless browser with stealth settings.
    Includes aggressive resolution for Google News redirects.
    """
    if os.getenv("RENDER") or not _HAS_PLAYWRIGHT or async_playwright is None:
        return {"success": False, "error": "Playwright disabled on cloud container.", "html": ""}

    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)

            # Create context with specific user agent
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            # Apply stealth plugin if available to bypass bot detection
            if _HAS_STEALTH:
                await Stealth().apply_stealth_async(page)

            logger.info("Playwright fetching: %s", url)

            # Navigate to URL
            # Use 'domcontentloaded' with settle pause to avoid timing out on heavy trackers/video
            try:
                response = await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            except Exception as goto_err:
                logger.warning("Playwright initial goto: %s. Continuing...", goto_err)
            
            await page.wait_for_timeout(2500)

            # --- AGGRESSIVE REDIRECT RESOLUTION ---
            # If we are still on a Google News URL, we need to wait for the JS/Meta redirect
            max_redirect_attempts = 5
            for i in range(max_redirect_attempts):
                current_url = page.url
                if "news.google.com" not in current_url:
                    break

                logger.info("Still on Google News redirect (attempt %d/%d), waiting...", i+1, max_redirect_attempts)
                try:
                    # Wait for the URL to change or for a common article element to appear
                    await page.wait_for_function(
                        f'() => window.location.href !== "{current_url}"',
                        timeout=3000
                    )
                except Exception:
                    # If timeout, we just try one more time or proceed to see if we landed
                    pass

            # Final resolved URL
            final_url = page.url

            # Now check the final response status
            # Note: response from goto is for the FIRST page.
            # For the final page, we check the current state.
            if "news.google.com" in final_url:
                logger.warning("Failed to escape Google News redirect wrapper for %s", url)

            # Get the rendered HTML safely
            try:
                content = await page.content()
            except Exception:
                await page.wait_for_timeout(1500)
                content = await page.content()
            await browser.close()

            return {"success": True, "html": content, "url": final_url}

    except Exception as e:
        logger.error("Playwright exception for %s: %s", url, e)
        return {"success": False, "error": str(e), "html": ""}

def sync_fetch_with_playwright(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    Synchronous wrapper for the async playwright fetcher.
    """
    try:
        return asyncio.run(fetch_with_playwright(url, timeout))
    except Exception as e:
        logger.error("Asyncio run error: %s", e)
        return {"success": False, "error": str(e), "html": ""}
