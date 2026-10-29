# claim_extractor.py
"""
Claim extraction module for BeyondBinary.
Splits text into sentences using spaCy and filters for check-worthy factual claims
using the ClaimBuster DeBERTa-v2 classifier.
"""

import logging
from typing import List
import spacy
from transformers import pipeline

logger = logging.getLogger("BeyondBinary.ClaimExtractor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Lazy loaded models
_nlp = None
_classifier = None

def get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy sentence segmenter (en_core_web_sm)...")
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            import spacy.cli
            logger.info("Downloading spaCy model 'en_core_web_sm'...")
            spacy.cli.download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_classifier():
    global _classifier
    if _classifier is None:
        logger.info("Loading ClaimBuster-DeBERTaV2 classifier...")
        try:
            _classifier = pipeline(
                "text-classification",
                model="whispAI/ClaimBuster-DeBERTaV2",
                low_cpu_mem_usage=True
            )
        except Exception:
            _classifier = pipeline(
                "text-classification",
                model="whispAI/ClaimBuster-DeBERTaV2"
            )
    return _classifier


def extract_claims(text: str, max_claims: int = 5) -> List[str]:
    """
    Extracts up to `max_claims` check-worthy factual claims from input text.
    Uses structural factual heuristic ranking + ClaimBuster DeBERTa-v2 with tight max_length
    to guarantee sub-second execution on CPU.
    """
    if not text or not text.strip():
        return []

    doc = get_nlp()(text)
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 15]
    if not sentences:
        return []

    # Fast heuristic ranking for check-worthy factual statements (CFS):
    # Prioritizes statistical assertions, numerical metrics, quotes, and named entities
    def _factual_rank(s: str) -> float:
        score = 0.0
        if any(c.isdigit() for c in s):
            score += 2.5
        if any(sym in s for sym in ["$", "£", "€", "%", "₹", "billion", "million", "percent"]):
            score += 2.5
        if any(w in s.lower() for w in ["said", "announced", "reported", "confirmed", "found", "stated", "arrested", "suspended"]):
            score += 1.5
        if '"' in s or "“" in s or "”" in s:
            score += 1.0
        if 15 <= len(s.split()) <= 45:
            score += 1.0
        return score

    ranked_candidates = sorted(sentences, key=_factual_rank, reverse=True)
    eval_candidates = ranked_candidates[:6]  # Evaluate top 6 highest-yield factual assertions

    try:
        classifier = get_classifier()
        scored = classifier(eval_candidates, truncation=True, max_length=128)
        claims = [
            sent for sent, result in zip(eval_candidates, scored)
            if ("CFS" in result["label"] or "Check-worthy" in result["label"]) and result["score"] >= 0.40
        ]
        if not claims and eval_candidates:
            claims = [eval_candidates[0]]
    except Exception as e:
        logger.warning("ClaimBuster classifier evaluation fallback: %s", e)
        claims = eval_candidates[:max_claims]

    return claims[:max_claims]