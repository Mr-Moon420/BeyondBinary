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

# Load spaCy pipeline once at module import
logger.info("Loading spaCy sentence segmenter (en_core_web_sm)...")
nlp = spacy.load("en_core_web_sm")

# Load ClaimBuster classifier once at module import
logger.info("Loading ClaimBuster-DeBERTaV2 classifier...")
classifier = pipeline(
    "text-classification",
    model="whispAI/ClaimBuster-DeBERTaV2"
)


def extract_claims(text: str, max_claims: int = 5) -> List[str]:
    """
    Extracts up to `max_claims` check-worthy factual claims from input text.
    Filters sentences that are classified as CFS (Check-worthy Factual Statement)
    with confidence > 0.5. If none exceed the threshold, falls back to the top candidate.
    """
    if not text or not text.strip():
        return []

    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 10]
    if not sentences:
        return []

    scored = classifier(sentences, truncation=True, max_length=512)

    logger.debug("Evaluated %d sentences for check-worthiness.", len(sentences))
    for sent, result in zip(sentences, scored):
        logger.debug("Sentence: '%s' | Label: %s | Score: %.3f", sent[:50], result["label"], result["score"])

    claims = [
        sent for sent, result in zip(sentences, scored)
        if ("CFS" in result["label"] or "Check-worthy" in result["label"]) and result["score"] >= 0.45
    ]

    if not claims and sentences:
        # Fallback: select candidate with highest check-worthiness score or top sentence
        cfs_candidates = [
            (result["score"] if ("CFS" in result["label"] or "Check-worthy" in result["label"]) else 0.0, sent)
            for sent, result in zip(sentences, scored)
        ]
        cfs_candidates.sort(key=lambda x: x[0], reverse=True)
        claims = [cfs_candidates[0][1]]

    return claims[:max_claims]