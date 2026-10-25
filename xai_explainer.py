# xai_explainer.py
"""
Explainable AI (XAI) module for BeyondBinary automated fact-checking.
Performs lightweight, deterministic semantic diagnostics (temporal timelines,
numerical scales, polarity negations, and entity overlaps) without heavy model dependencies.
Generates transparent, token-level diagnostic rationales for college & journalistic audit defense.
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("BeyondBinary.XAIExplainer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _extract_years(text: str) -> List[str]:
    """Extract 4-digit years (1900-2099) from text."""
    matches = re.findall(r"\b(19\d\d|20\d\d)\b", text)
    return list(dict.fromkeys(matches))


def _extract_numbers(text: str) -> List[str]:
    """Extract quantities, counts, and percentages from text."""
    matches = re.findall(
        r"\b(?:\$\d+(?:\.\d+)?(?:\s*(?:billion|million|trillion))?|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?%)\b",
        text,
        re.IGNORECASE
    )
    clean = [m for m in matches if m not in ("2020", "2021", "2022", "2023", "2024", "2025", "2026")]
    return list(dict.fromkeys(clean))


STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those", "and", "or", "but",
    "in", "on", "at", "to", "for", "with", "by", "from", "of", "about",
    "it", "its", "they", "them", "their", "we", "our", "you", "your",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had"
}

def _extract_proper_entities(text: str) -> List[str]:
    """
    Extracts multi-word proper nouns and capitalized entity names (e.g., 'James Webb Space Telescope', 'NASA').
    """
    # Matches consecutive capitalized words
    pattern = r"\b[A-Z][a-zA-Z0-9]*(?:'[a-z]+)?(?:\s+[A-Z][a-zA-Z0-9]*(?:'[a-z]+)?)*\b"
    matches = re.findall(pattern, text)
    clean = []
    for m in matches:
        m_str = m.strip()
        if len(m_str) > 2 and m_str.lower() not in STOPWORDS:
            clean.append(m_str)
    return list(dict.fromkeys(clean))


NEGATION_WORDS = {
    "not", "never", "no", "failed", "denied", "refused", "dismissed",
    "rejected", "untrue", "false", "hoax", "debunked", "blocked", "disproven", "fake"
}


def explain_verification(
    claim: str,
    verdict: str,
    confidence: float,
    evidence: List[str],
    retrieval_source: str = "Knowledge Corpus",
    framing_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Produces structured XAI rationale and entity-level diagnostic diffs.
    """
    clean_claim = (claim or "").strip()
    ev_snippets = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
    top_evidence = " ".join(ev_snippets[:3])
    framing_info = framing_info or {}

    claim_years = _extract_years(clean_claim)
    ev_years = _extract_years(top_evidence)

    claim_nums = _extract_numbers(clean_claim)
    ev_nums = _extract_numbers(top_evidence)

    claim_entities = _extract_proper_entities(clean_claim)
    ev_entities = _extract_proper_entities(top_evidence)

    conflict_diff: List[Dict[str, str]] = []
    category = "Corroborating Alignment"
    rationale = ""
    alignment_entities: List[str] = []

    # 1. TEMPORAL CHECK: Check for year discrepancies in contested claims
    if claim_years and ev_years and verdict in ("Refuted", "Misleading-Framing", "Not Enough Info"):
        common_years = set(claim_years).intersection(set(ev_years))
        if not common_years:
            c_yr = claim_years[0]
            e_yr = ev_years[0]
            category = "Temporal Inconsistency"
            conflict_diff.append({
                "type": "Timeline / Year",
                "claim_val": c_yr,
                "evidence_val": e_yr
            })
            rationale = (
                f"Timeline discrepancy detected: The claim asserts an event occurred in {c_yr}, "
                f"whereas verified reporting retrieved from {retrieval_source} documents the occurrence in {e_yr}."
            )

    # 2. QUANTITATIVE / NUMERICAL CHECK: Check for conflicting numbers
    if not conflict_diff and claim_nums and ev_nums and verdict in ("Refuted", "Misleading-Framing"):
        c_num = claim_nums[0]
        e_num = ev_nums[0]
        if c_num != e_num:
            category = "Quantitative / Scale Disparity"
            conflict_diff.append({
                "type": "Metric / Scale",
                "claim_val": c_num,
                "evidence_val": e_num
            })
            rationale = (
                f"Scale disparity detected: The claim cites {c_num}, whereas retrieved evidence "
                f"documents {e_num}, reflecting potential quantitative distortion."
            )

    # 3. POLARITY INVERSION CHECK (Negation / Denial)
    claim_tokens = {re.sub(r"[^a-z]", "", t.lower()) for t in clean_claim.split()}
    ev_tokens = {re.sub(r"[^a-z]", "", t.lower()) for t in top_evidence.split()}
    has_ev_negation = bool(ev_tokens.intersection(NEGATION_WORDS))
    has_claim_negation = bool(claim_tokens.intersection(NEGATION_WORDS))

    if not conflict_diff and verdict == "Refuted":
        if has_ev_negation and not has_claim_negation:
            category = "Polarity / Action Inversion"
            neg_found = list(ev_tokens.intersection(NEGATION_WORDS))[0]
            conflict_diff.append({
                "type": "Semantic Polarity",
                "claim_val": "Affirmative Assertion",
                "evidence_val": f"Negated / Refuted ('{neg_found}')"
            })
            rationale = (
                f"Direct refutation detected: The claim alleges an affirmative action, but retrieved evidence "
                f"explicitly negates or disputes the proposition (using '{neg_found}')."
            )

    # 4. SENSATIONALIST / RHETORICAL FRAMING CHECK
    detected_markers = framing_info.get("detected_markers", [])
    if not conflict_diff and (verdict == "Misleading-Framing" or (detected_markers and verdict == "Refuted")):
        category = "Sensationalist Framing"
        marker_str = ", ".join([f"'{m}'" for m in detected_markers[:3]]) if detected_markers else "loaded modifiers"
        rationale = (
            f"Framing distortion detected: The assertion employs emotive, pejorative language ({marker_str}) "
            f"to introduce subjective spin beyond established factual consensus."
        )

    # 5. SUPPORTED / CORROBORATING ALIGNMENT
    if verdict == "Supported":
        category = "Verified Corroboration"
        # Find shared actors or topics
        shared = [e for e in claim_entities if any(e.lower() in ev.lower() for ev in ev_snippets)]
        alignment_entities = shared[:4]
        topic_str = f"regarding {', '.join(alignment_entities[:2])}" if alignment_entities else "in the premise"
        rationale = (
            f"Corroborating alignment confirmed: Independent reporting from {retrieval_source} "
            f"directly substantiates the core factual assertions {topic_str} with consistent contextual facts."
        )

    # 6. NOT ENOUGH INFO / INSUFFICIENT GROUNDING
    if verdict == "Not Enough Info" and not rationale:
        category = "Insufficient Evidence Grounding"
        rationale = (
            f"Insufficient grounding: While external news feeds and knowledge bases were consulted, "
            f"available corpus passages do not contain enough overlapping factual entities to conclusively corroborate or refute this assertion."
        )

    # Default fallback rationale if still empty
    if not rationale:
        if verdict == "Refuted":
            category = "Premise Contradiction"
            rationale = (
                f"Contradiction identified: RoBERTa-large natural language inference determined that "
                f"the evidence gathered from {retrieval_source} statistically contradicts the claim with {round(confidence * 100)}% confidence."
            )
        elif verdict == "Supported":
            category = "Premise Entailment"
            rationale = (
                f"Entailment verified: The retrieved evidence logically entails the claim premise "
                f"with {round(confidence * 100)}% model confidence."
            )
        else:
            category = "Neutral Context"
            rationale = "The retrieved context is neutral or inconclusive relative to the specific assertion."

    return {
        "category": category,
        "rationale": rationale,
        "conflict_diff": conflict_diff,
        "alignment_entities": alignment_entities,
        "flagged_markers": detected_markers
    }
