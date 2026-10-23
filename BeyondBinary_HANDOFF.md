# BeyondBinary Project Handover

## Project Overview
BeyondBinary is a multi-dimensional media credibility and bias analysis tool. It extracts factual claims from news articles, verifies them using real-time web evidence, and analyzes the political framing and bias of the source.

## System Architecture

### 1. Backend (FastAPI)
- **`main.py`**: The central orchestrator. Manages the API endpoints for analysis and the trending news feed.
- **`claim_extractor.py`**: Uses a DeBERTaV2 model to identify check-worthy factual claims.
- **`verifier.py`**: Integrates with a search provider to find evidence and an NLI model to determine if a claim is Supported, Refuted, or Neutral.
- **`bias_detector.py`**: Analyzes political leaning using a BERT-based model and a knowledge base (AllSides).
- **`scorer.py`**: Computes a final credibility score based on the verification results of extracted claims.

### 2. Fetching Pipeline (The "Four-Tier" Strategy)
To combat aggressive bot detection on news sites, the system uses a tiered fallback mechanism in `article_fetcher.py`:
1.  **Tier 1: Direct Request** (`requests`) - Fastest, works for open sites.
2.  **Tier 1.5: Browser Emulation** (`playwright_fetcher.py`) - Uses a headless Chromium browser with `playwright-stealth` to bypass bot detection and render JavaScript.
3.  **Tier 2: Aggregator** (`news_provider.py`) - Uses GNews API to retrieve indexed summaries.
4.  **Tier 3: RSS Fallback** (`feedParsing.py`) - Extracts content from site-specific RSS feeds.

### 3. Trending Feed
- **Mechanism**: Now powered by **Google News RSS**.
- **Resolution**: The system resolves Google's redirect links to actual article URLs before sending them to the frontend.
- **Filtering**: Implements path-depth heuristics to filter out category landing pages (e.g., `/politics`) in favor of specific article slugs.

### 4. Frontend
- **`index.html`**: A single-page application (SPA) using vanilla JS and CSS.
- **UI/UX**: Features a credibility score circle, a political spectrum pin, and a a detailed claim-by-claim verification list.

## Current Issues & Technical Debt (CRITICAL)

### 🔴 High Priority
- **Home Screen Loading**: The `/trending` endpoint is currently unstable. While the Google News RSS feed returns data, the frontend is occasionally failing to render these articles.
- **Fetching Reliability**: Despite the 4-tier system, many high-authority sites still block all attempts. The "could not fetch" error persists for a significant percentage of URLs.
- **URL Field UI**: While fixed to prevent page stretching, the input field in the analyzer may still require better UX for handling extremely long URLs.

### 🟡 Medium Priority
- **Redirect Latency**: Resolving Google News URLs in the `/trending` loop adds a network round-trip per article, increasing response time.
- **Publisher Matching**: Publisher bias lookup currently relies on simple domain/name matching which may miss some outlets.

## Setup & Dependencies
- **Python 3.12+**
- **Key Dependencies**: `fastapi`, `playwright`, `playwright-stealth`, `lxml`, `requests`.
- **Required Environment Variables**:
  - `BRAVE_API_KEY`: For factual evidence retrieval.
  - `GNEWS_API_KEY`: For the aggregator fallback.
- **Browser Setup**: Must run `python -m playwright install chromium` to enable the stealth fetcher.

## Future Roadmap
- Implement randomized User-Agents and Viewports in `playwright_fetcher.py`.
- Move the trending feed to a cached background task to reduce API latency.
- Integrate a professional proxy service (e.g., ScraperAPI) to eliminate the remaining blockages.
