# verifier.py
"""
Verifier module for BeyondBinary.
Performs semantic retrieval against local FAISS index, multi-tier real-time web/wiki
evidence retrieval via search_provider, NLI inference with RoBERTa-large-MNLI,
and transparent Explainable AI (XAI) rationale synthesis.
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
from xai_explainer import explain_verification

logger = logging.getLogger("BeyondBinary.Verifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Lazy loading for embedding and NLI models
_embedder = None
_nli = None

def get_embedder():
    global _embedder
    if _embedder is None:
        logger.info("Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_nli():
    global _nli
    if _nli is None:
        logger.info("Initializing RoBERTa NLI pipeline (roberta-large-mnli)...")
        _nli = pipeline("text-classification", model="roberta-large-mnli")
    return _nli

# Relative path loading for FAISS index and passages
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    1. Checks local FAISS index for high-confidence local passage matches (distance <= 0.70).
    2. If distance > 0.70, queries multi-tier real-time web & Wikipedia evidence provider.
    3. If neither web evidence nor high-confidence local passage exists (dist > 0.85),
       gracefully tags as 'Not Enough Info' rather than hallucinating refutation.
    4. Runs premise/hypothesis NLI classification with RoBERTa-large-MNLI.
    5. Computes calibrated verdict and confidence score.
    6. Generates Explainable AI (XAI) rationale and entity-level diagnostic diffs.
    """
    embedding = get_embedder().encode([claim]).astype("float32")
    distances, indices = index.search(embedding, k=2)

    dist_val = float(distances[0][0])
    logger.info("Verifying claim: '%s' (FAISS distance: %.3f)", claim[:60], dist_val)

    retrieval_source = "Local FAISS Index"
    sources: List[Dict[str, Any]] = []
    evidence: List[str] = []

    # If local evidence is not closely matched (distance > 0.70), query live multi-tier search
    if dist_val > 0.70:
        web_evidence, web_sources = fetch_web_evidence(claim, max_results=3)
        if web_evidence:
            evidence = web_evidence
            sources = web_sources
            primary_src = web_sources[0].get("source_type", "Live Web Search") if web_sources else "Live Web Search"
            retrieval_source = f"{primary_src} (Live Corroboration)"
            logger.info("Using web evidence (%d snippets, primary: %s)", len(evidence), primary_src)

    # If no web evidence found, use local FAISS only if distance is reasonably bounded (<= 0.85)
    if not evidence:
        if dist_val <= 0.85:
            evidence = [passages[i] for i in indices[0] if i < len(passages)]
            sources = [
                {"title": f"Local Wiki Corpus #{i}", "url": "", "snippet": passages[i], "source_type": "Local FAISS Index"}
                for i in indices[0] if i < len(passages)
            ]
            retrieval_source = "Local FAISS Index"
        else:
            logger.info("Claim has no corroborating local or web evidence (FAISS dist %.3f > 0.85)", dist_val)
            xai_info = explain_verification(
                claim=claim,
                verdict="Not Enough Info",
                confidence=0.50,
                evidence=[],
                retrieval_source="Unverified (Insufficient Corroboration)",
                framing_info=None
            )
            return {
                "claim": claim,
                "verdict": "Not Enough Info",
                "confidence": 0.50,
                "evidence": [],
                "sources": [],
                "retrieval_source": "Unverified (Insufficient Corroboration)",
                "framing_analysis": {
                    "is_misleading": False,
                    "framing_type": None,
                    "detected_markers": [],
                    "density_pct": 0.0,
                    "explanation": "No authoritative corroborating evidence was found in the local archive or live web."
                },
                "xai_rationale": xai_info
            }

    # Evaluate evidence against claim using RoBERTa NLI (Premise: evidence, Hypothesis: claim)
    verdicts = []
    confidences = []
    verdict_scores: Dict[str, List[float]] = {}

    for ev in evidence:
        clean_ev = ev.strip()
        if not clean_ev:
            continue
        try:
            res = get_nli()({"text": clean_ev, "text_pair": claim}, truncation=True, max_length=512)
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
        xai_info = explain_verification(
            claim=claim,
            verdict="Not Enough Info",
            confidence=0.50,
            evidence=evidence,
            retrieval_source=retrieval_source,
            framing_info=None
        )
        return {
            "claim": claim,
            "verdict": "Not Enough Info",
            "confidence": 0.50,
            "evidence": evidence,
            "sources": sources,
            "retrieval_source": retrieval_source,
            "framing_analysis": {
                "is_misleading": False,
                "framing_type": None,
                "detected_markers": [],
                "density_pct": 0.0,
                "explanation": "NLI evaluation could not score the retrieved snippets."
            },
            "xai_rationale": xai_info
        }

    # Evaluate claim framing (loaded rhetoric, evidence divergence, sensationalism)
    framing_info = evaluate_claim_framing(claim, verdicts, evidence)

    # Compute raw NLI vote counts
    entailment_count = verdicts.count("ENTAILMENT")
    contradiction_count = verdicts.count("CONTRADICTION")
    neutral_count = verdicts.count("NEUTRAL")

    # Decision logic for final verdict:
    # 1. If at least one authoritative passage corroborates and entails the claim -> Supported
    if entailment_count > 0 and entailment_count >= contradiction_count:
        mapped_verdict = "Supported"
        # Prioritize the corroborating evidence passage for display
        for idx_ev, v in enumerate(verdicts):
            if v == "ENTAILMENT":
                evidence = [evidence[idx_ev]] + [e for j, e in enumerate(evidence) if j != idx_ev]
                if sources and idx_ev < len(sources):
                    sources = [sources[idx_ev]] + [s for j, s in enumerate(sources) if j != idx_ev]
                break
    elif contradiction_count > 0 and contradiction_count > entailment_count:
        mapped_verdict = "Refuted"
    elif framing_info.get("is_misleading"):
        mapped_verdict = "Misleading-Framing"
    else:
        mapped_verdict = "Not Enough Info"

    # Calibrated confidence calculation
    if mapped_verdict == "Misleading-Framing":
        base_conf = max(confidences) if confidences else 0.8
        avg_confidence = round(min(0.98, max(0.75, base_conf)), 3)
    else:
        # Match winning label
        target_label = "ENTAILMENT" if mapped_verdict == "Supported" else ("CONTRADICTION" if mapped_verdict == "Refuted" else "NEUTRAL")
        winning_scores = verdict_scores.get(target_label, confidences)
        avg_confidence = round(sum(winning_scores) / len(winning_scores), 3) if winning_scores else 0.70

    # Generate Explainable AI (XAI) rationale and entity-level diagnostics
    xai_info = explain_verification(
        claim=claim,
        verdict=mapped_verdict,
        confidence=avg_confidence,
        evidence=evidence,
        retrieval_source=retrieval_source,
        framing_info=framing_info
    )

    return {
        "claim": claim,
        "verdict": mapped_verdict,
        "confidence": avg_confidence,
        "evidence": evidence,
        "sources": sources,
        "retrieval_source": retrieval_source,
        "framing_analysis": framing_info,
        "xai_rationale": xai_info
    }
