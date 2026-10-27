---
title: BeyondBinary - Media Credibility & Bias Analysis
emoji: ⚖️
colorFrom: gray
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# BeyondBinary

**BeyondBinary** is a multi-dimensional media credibility and ideological bias analysis system. It combines Natural Language Inference (NLI), semantic vector retrieval, Explainable AI (XAI) diagnostics, and domain-level media intelligence to evaluate the factual accuracy, rhetorical framing, and polarization of news reporting.

---

## 🤖 Neural Model Architecture

BeyondBinary utilizes a modular, multi-tier AI pipeline:

| Module | Model / Service | Technical Function |
| :--- | :--- | :--- |
| **Claim Extractor** | `ClaimBuster-DeBERTaV2` | Scans raw text and extracts check-worthy factual assertions (CFS). |
| **Verifier (NLI)** | `RoBERTa-large-MNLI` | Evaluates premise-hypothesis entailment (`Supported`, `Refuted`, `Not Enough Info`). |
| **Semantic Retrieval** | `all-MiniLM-L6-v2` + `FAISS` | 384-dimensional dense vector embeddings for high-speed local corpus retrieval. |
| **Live Grounding** | `Brave Search API` + Wikipedia | Real-time authoritative evidence retrieval for breaking news events. |
| **XAI Diagnostics** | `xai_explainer` (NLP Engine) | Deterministic timeline conflict, numerical scale variance, and entity diff diagnostics. |
| **Political Bias** | `mbzuai-political-bias-bert` | Classifies ideological slant (Left, Center, Right) from semantic patterns. |
| **Media Intelligence**| `AllSides Knowledge Base` | Ground-truth publisher ratings for 101 authoritative global news outlets. |

---

## 📁 Repository Directory Structure

```
BeyondBinary/
├── backend/                     # Python Backend Services & Neural Models
│   ├── __init__.py              # Package initializer & path setup
│   ├── main.py                  # FastAPI application & API endpoints
│   ├── verifier.py              # RoBERTa-large NLI & verification engine
│   ├── claim_extractor.py       # ClaimBuster DeBERTa claim extraction
│   ├── bias_detector.py         # Political Bias BERT & AllSides grounding
│   ├── scorer.py                # Credibility calibration & penalty scoring
│   ├── xai_explainer.py         # Explainable AI diagnostics & conflict diffs
│   ├── search_provider.py       # Brave Search API & Wikipedia provider
│   ├── article_fetcher.py       # Multi-tier web article scraper
│   ├── playwright_fetcher.py    # Playwright stealth browser crawler
│   ├── news_provider.py         # News aggregator client
│   └── feed_parser.py           # RSS XML feed parsing
│
├── frontend/                    # Modern React + Vite + Tailwind CSS Application
│   ├── src/                     # Broadsheet components, hooks & services
│   ├── dist/                    # Production built bundle (served by FastAPI)
│   └── package.json
│
├── data/                        # Static indices & Knowledge Bases
│   ├── fever_index.faiss        # FAISS vector index
│   ├── passages.pkl             # Reference knowledge passages
│   ├── allsides_ratings.json    # AllSides media rating database
│
├── scripts/                     # Developer utilities & test scripts
│   └── build_index.py           # Offline FAISS index generator
│
├── docs/                        # Formal Documentation
│   └── ARCHITECTURE.md          # Technical specifications & mathematical formulas
│
├── main.py                      # Root entrypoint (forwards to backend.main:app)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # Primary documentation
```

---

## 🧮 Mathematical Formulations

### 1. Composite Credibility Score ($0 - 100$)
$$S = 100 \times \left( \frac{\sum_{i=1}^N w_i \cdot \mathbb{I}(v_i)}{\sum_{i=1}^N w_i} \right) - \lambda \cdot D_{\text{loaded}}$$

- $\mathbb{I}(\text{Supported}) = 1.0$, $\mathbb{I}(\text{Not Enough Info}) = 0.5$, $\mathbb{I}(\text{Refuted}) = 0.0$
- $w_i = \text{confidence}_i$ from RoBERTa-large-MNLI softmax probability
- $D_{\text{loaded}}$ is the sensationalist lexical density percentage ($\lambda = 0.5$).

### 2. Polarization Index (Echo-Chamber Deck)
$$\text{TVD}(P_A, P_B) = \frac{1}{2} \sum_{c \in \{L, C, R\}} |P_A(c) - P_B(c)|$$
$$\text{Polarization Index} = \min\left(100, 100 \times \left(0.70 \cdot \text{TVD} + 0.30 \cdot |\text{DomainBias}_A - \text{DomainBias}_B|\right)\right)$$

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (Recommended: 3.11 or 3.12)
- Node.js 18+ (for frontend modifications, optional for runtime)
- Brave Search API Key (configured in `.env`)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Mr-Moon420/BeyondBinary.git
cd BeyondBinary

# Set up virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m playwright install chromium

# Configure API Key
cp .env.example .env
# Edit .env and paste your BRAVE_API_KEY
```

### 3. Running the Server
```bash
# Run backend server (serves both API and production UI)
uvicorn main:app --host 127.0.0.1 --port 8001
```
Open your browser at **`http://127.0.0.1:8001`**.
