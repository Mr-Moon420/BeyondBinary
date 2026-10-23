# verifier.py
"""
Verifier module for BeyondBinary.
Performs semantic retrieval against local FAISS index, real-time web evidence
retrieval via Brave Search API, and NLI inference with RoBERTa-large-MNLI.
"""

import os
import pickle
import logging
from typing import Dict, Any, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from search_provider import fetch_web_evidence, get_search_provider
from bias_detector import evaluate_claim_framing

logger = logging.getLogger("BeyondBinary.Verifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Load embedding and NLI models
logger.info("Initializing SentenceTransformer and RoBERTa NLI pipeline...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
nli = pipeline("text-classification", model="roberta-large-mnli")

# Robust relative path loading for FAISS index and passages
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
index_path = os.path.join(BASE_DIR, "data", "fever_index.faiss")
passages_path = os.path.join(BASE_DIR, "data", "passages.pkl")

index = faiss.read_index(index_path)
with open(passages_path, "rb") as f:
    passages = pickle.load(f)

LABEL_MAP = {
    "ENTAILMENT": "Supported",
    "CONTRADICTION": "Refuted",
    "NEUTRAL": "Not Enough Info"
}


def verify_claim(claim: str) -> Dict[str, Any]:
    """
    Verifies a factual claim using semantic retrieval and web search:
    1. Checks local FAISS index for high-confidence local passage matches.
    2. If distance > 0.8 (insufficient local match) or if Brave Search is configured,
       retrieves authoritative real-time web search evidence via Brave Search API.
    3. Runs premise/hypothesis NLI classification with RoBERTa-large-MNLI.
    4. Computes majority verdict and calibrated confidence score.
    """
    embedding = embedder.encode([claim]).astype("float32")
    distances, indices = index.search(embedding, k=2)

    dist_val = float(distances[0][0])
    logger.info("Verifying claim: '%s' (FAISS nearest distance: %.3f)", claim[:60], dist_val)

    retrieval_source = "Local FAISS Index"
    sources: List[Dict[str, Any]] = []
    evidence: List[str] = []

    # If local evidence is not closely matched (distance > 0.8), query Brave Search
    search_provider = get_search_provider()
    if dist_val > 0.8:
        if search_provider.is_configured:
            web_evidence, web_sources = fetch_web_evidence(claim, max_results=3)
            if web_evidence:
                evidence = web_evidence
                sources = web_sources
                retrieval_source = "Brave Web Search"
                logger.info("Using Brave Web Search evidence (%d snippets)", len(evidence))
        else:
            logger.info("Brave API key not configured; falling back to local FAISS passages.")

    # Fallback to local FAISS passages if no web evidence was retrieved
    if not evidence:
        evidence = [passages[i] for i in indices[0] if i < len(passages)]
        sources = [
            {"title": f"Local Wiki Corpus #{i}", "url": "", "snippet": passages[i]}
            for i in indices[0] if i < len(passages)
        ]
        retrieval_source = "Local FAISS Index"

    # Evaluate evidence against claim using RoBERTa NLI (Premise: evidence, Hypothesis: claim)
    verdicts = []
    confidences = []
    verdict_scores: Dict[str, List[float]] = {}

    for ev in evidence:
        clean_ev = ev.strip()
        if not clean_ev:
            continue
        try:
            # Pair input: text = premise (evidence), text_pair = hypothesis (claim)
            res = nli({"text": clean_ev, "text_pair": claim}, truncation=True, max_length=512)
            if isinstance(res, list):
                res = res[0]
            label = res["label"]
            score = float(res["score"])

            verdicts.append(label)
            confidences.append(score)
            verdict_scores.setdefault(label, []).append(score)
        except Exception as e:
            logger.warning("NLI classification failed for snippet: %s", e)

    if not verdicts:
        return {
            "claim": claim,
            "verdict": "Not Enough Info",
            "confidence": 0.5,
            "evidence": evidence,
            "sources": sources,
            "retrieval_source": retrieval_source,
            "framing_analysis": {
                "is_misleading": False,
                "framing_type": None,
                "detected_markers": [],
                "density_pct": 0.0,
                "explanation": "No evidence retrieved to evaluate framing."
            }
        }

    # Evaluate claim framing (loaded rhetoric, evidence divergence, sensationalism)
    framing_info = evaluate_claim_framing(claim, verdicts, evidence)

    # Compute raw NLI majority vote
    final_label = max(set(verdicts), key=verdicts.count)
    contradiction_ratio = verdicts.count("CONTRADICTION") / len(verdicts)

    # Decision logic for final verdict:
    # 1. Clear factual contradiction takes precedence -> Refuted
    # 2. If claim uses loaded language / exhibits framing conflict -> Misleading-Framing
    # 3. Else standard NLI mapping (Supported / Not Enough Info)
    if final_label == "CONTRADICTION" and contradiction_ratio >= 0.5:
        mapped_verdict = "Refuted"
    elif framing_info["is_misleading"]:
        mapped_verdict = "Misleading-Framing"
    elif final_label == "ENTAILMENT":
        mapped_verdict = "Supported"
    else:
        mapped_verdict = "Not Enough Info"

    # Calibrated confidence calculation
    if mapped_verdict == "Misleading-Framing":
        base_conf = max(confidences) if confidences else 0.8
        avg_confidence = round(min(0.98, max(0.75, base_conf)), 3)
    else:
        winning_scores = verdict_scores.get(final_label, confidences)
        avg_confidence = round(sum(winning_scores) / len(winning_scores), 3)

    return {
        "claim": claim,
        "verdict": mapped_verdict,
        "confidence": avg_confidence,
        "evidence": evidence,
        "sources": sources,
        "retrieval_source": retrieval_source,
        "framing_analysis": framing_info
    }