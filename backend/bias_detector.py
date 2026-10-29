# bias_detector.py
"""
Political Bias and Framing Analysis module for BeyondBinary.
Combines:
1. AllSides Media Bias knowledge base lookup (domain-level ground truth).
2. Partisan stance NLP classification via fine-tuned BERT (theArif/mbzuai-political-bias-bert).
3. Loaded-language / sensationalism density analysis.
4. Cross-source coverage distribution across the political spectrum.
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import requests

import torch
import numpy as np
from transformers import pipeline
import threading
from model_runtime import pipeline_options, inference_slot

logger = logging.getLogger("BeyondBinary.BiasDetector")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Load AllSides Media Bias Database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLSIDES_FILE = os.path.join(BASE_DIR, "data", "allsides_ratings.json")

ALLSIDES_RATINGS: Dict[str, Dict[str, Any]] = {}
if os.path.exists(ALLSIDES_FILE):
    try:
        with open(ALLSIDES_FILE, "r", encoding="utf-8") as f:
            ALLSIDES_RATINGS = json.load(f)
        logger.info("Loaded %d AllSides domain ratings from %s", len(ALLSIDES_RATINGS), ALLSIDES_FILE)
    except Exception as e:
        logger.error("Failed to load allsides_ratings.json: %s", e)
else:
    logger.warning("allsides_ratings.json not found at %s", ALLSIDES_FILE)

MODEL_NAME = "theArif/mbzuai-political-bias-bert"
_bias_classifier = None
_bias_classifier_lock = threading.RLock()

def get_bias_classifier():
    with _bias_classifier_lock:
        return _load_bias_classifier()


def _load_bias_classifier():
    global _bias_classifier
    if _bias_classifier is None:
        logger.info("Loading political bias model '%s'...", MODEL_NAME)
        try:
            import torch
            _bias_classifier = pipeline(
                "text-classification",
                model=MODEL_NAME,
                top_k=None,
                truncation=True,
                max_length=128,
                **pipeline_options()
            )
            logger.info("Political bias model ready on %s", _bias_classifier.device)
        except Exception as e:
            logger.warning("Preferred bias runtime failed; using CPU: %s", e)
            try:
                _bias_classifier = pipeline(
                    "text-classification",
                    model=MODEL_NAME,
                    top_k=None,
                    truncation=True,
                    max_length=128,
                    device=-1,
                    low_cpu_mem_usage=True
                )
            except Exception as e2:
                logger.error("Failed to load political bias model '%s': %s", MODEL_NAME, e2)
                _bias_classifier = None
    return _bias_classifier

# Curated partisan framing and loaded-language lexicon
LOADED_WORDS = {
    # Pejoratives, dehumanizing words & political slurs / mockery
    "cockroach", "cockroaches", "vermin", "parasite", "parasites", "thug", "thugs",
    "crony", "cronies", "mob", "goon", "goons", "puppet", "puppets", "stooge", "stooges",
    "clown", "clowns", "coward", "cowards", "moron", "morons", "lunatic", "deranged",
    "unhinged", "clueless", "incompetent", "corrupt", "corruption", "shameful", "disgrace",
    # Authoritarian, extremist & conspiracy framing
    "tyranny", "tyrant", "tyrannical", "authoritarian", "dictator", "regime", "despot",
    "cabal", "deepstate", "deep-state", "fascist", "fascists", "fascism", "nazi", "nazis",
    "socialist", "socialists", "communist", "communists", "marxist", "indoctrination",
    "brainwashed", "brainwashing", "censorship", "propaganda", "subversion", "sabotage",
    # Partisan hyperbole, sensational verbs & scandal framing
    "radical", "radicals", "extremist", "extremists", "fanatics", "fanatic", "traitor",
    "traitors", "treason", "treasonous", "witch-hunt", "witchhunt", "witch hunt",
    "disastrous", "catastrophe", "catastrophic", "draconian", "bloodbath", "nightmare",
    "slams", "blasts", "eviscerates", "gutted", "annihilated", "demolished", "destroyed",
    "sham", "scandal", "weaponized", "weaponize", "evil", "sinister", "nefarious",
    "scheming", "coverup", "cover-up", "hoax", "rigged", "fraud", "fraudulent",
    "hypocrisy", "hypocritical", "collusion", "conspiracy"
}


def evaluate_claim_framing(
    claim: str,
    nli_verdicts: List[str],
    evidence_snippets: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluates whether a factual claim exhibits Misleading-Framing based on:
    1. Emotionally charged, pejorative, or sensationalist rhetoric in the claim.
    2. Evidence conflict (divergence across multiple authoritative sources).
    3. Subjective spin applied to factual premises.
    """
    tokens = re.findall(r"\b[a-zA-Z-]+\b", claim.lower())
    detected_loaded = [w for w in tokens if w in LOADED_WORDS]

    # Check for multi-word partisan / sensationalist phrases
    claim_lower = claim.lower()
    sensational_phrases = [
        "witch hunt", "cover-up", "cover up", "fake news", "deep state",
        "kangaroo court", "puppet regime", "cabal of", "rigged system",
        "stolen election", "sham trial", "brainwashed public"
    ]
    detected_phrases = [p for p in sensational_phrases if p in claim_lower]

    # Check for contested / contradictory evidence across snippets
    unique_nli = set(nli_verdicts) if nli_verdicts else set()
    is_contested = ("ENTAILMENT" in unique_nli and "CONTRADICTION" in unique_nli)

    density_pct = (len(detected_loaded) / len(tokens) * 100) if tokens else 0.0

    is_misleading = False
    framing_type = None
    reasons = []

    if detected_loaded or detected_phrases:
        is_misleading = True
        framing_type = "Loaded Language & Pejorative Framing"
        all_markers = sorted(list(set(detected_loaded + detected_phrases)))
        markers_str = ", ".join(f"'{m}'" for m in all_markers[:4])
        reasons.append(f"Statement uses emotionally charged or derogatory rhetoric ({markers_str})")

    elif is_contested and len(evidence_snippets or []) >= 2:
        is_misleading = True
        framing_type = "Contested Evidence & Conflicting Reporting"
        reasons.append("Independent sources provide conflicting evidence (both entailment and contradiction), indicating contested factual framing")

    explanation = " · ".join(reasons) if reasons else "No misleading framing detected."

    return {
        "is_misleading": is_misleading,
        "framing_type": framing_type,
        "detected_markers": sorted(list(set(detected_loaded + detected_phrases))),
        "density_pct": round(density_pct, 2),
        "explanation": explanation
    }


def extract_domain(url_or_domain: str) -> Optional[str]:
    """Extracts clean base domain (e.g. 'cnn.com') from a URL or domain string."""
    if not url_or_domain:
        return None
    url_clean = url_or_domain.strip().lower()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean
    try:
        parsed = urlparse(url_clean)
        netloc = parsed.netloc or parsed.path
        netloc = netloc.split(":")[0]  # strip port if present
        # strip 'www.' prefix
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None


def lookup_domain_bias(url_or_domain: str) -> Optional[Dict[str, Any]]:
    """Checks AllSides database for a matching outlet domain."""
    domain = extract_domain(url_or_domain)
    if not domain:
        return None

    # Exact domain match
    if domain in ALLSIDES_RATINGS:
        res = dict(ALLSIDES_RATINGS[domain])
        res["domain"] = domain
        return res

    # Fallback to parent domain (e.g. news.bbc.co.uk -> bbc.co.uk)
    parts = domain.split(".")
    if len(parts) > 2:
        parent_domain = ".".join(parts[-2:])
        if parent_domain in ALLSIDES_RATINGS:
            res = dict(ALLSIDES_RATINGS[parent_domain])
            res["domain"] = parent_domain
            return res

    return None


def analyze_loaded_language(text: str) -> Dict[str, Any]:
    """
    Computes loaded language density and extracts emotionally charged/hyperbolic keywords.
    """
    tokens = re.findall(r"\b[a-zA-Z-]+\b", text.lower())
    if not tokens:
        return {"loaded_count": 0, "density_pct": 0.0, "detected_words": []}

    detected = [w for w in tokens if w in LOADED_WORDS]
    density = round((len(detected) / len(tokens)) * 100, 2)
    unique_detected = sorted(list(set(detected)))

    return {
        "loaded_count": len(detected),
        "total_words": len(tokens),
        "density_pct": density,
        "detected_words": unique_detected[:10]  # top 10 unique words
    }


def score_to_category(score: float) -> str:
    """Maps continuous spectrum score (-1.0 to +1.0) to AllSides category label."""
    if score <= -0.5:
        return "Left"
    elif score <= -0.15:
        return "Lean Left"
    elif score < 0.15:
        return "Center"
    elif score < 0.5:
        return "Lean Right"
    else:
        return "Right"


_HF_BIAS_AVAILABLE = True

def _query_hf_inference_bias(text: str) -> Optional[List[Dict[str, Any]]]:
    """Query Hugging Face Serverless Inference API with fast circuit breaker."""
    global _HF_BIAS_AVAILABLE
    if not _HF_BIAS_AVAILABLE:
        return None

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        return None
    try:
        url = "https://router.huggingface.co/hf-inference/models/theArif/mbzuai-political-bias-bert"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": text[:256],
            "options": {"wait_for_model": False}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0] if isinstance(data[0], list) else data
        else:
            logger.info("HF Bias API status %d. Tripping circuit breaker to local CPU engine.", resp.status_code)
            _HF_BIAS_AVAILABLE = False
    except Exception as e:
        logger.warning("HF Serverless Bias API error: %s", e)
        _HF_BIAS_AVAILABLE = False
    return None


def classify_text_stance(text: str) -> Dict[str, Any]:
    """
    Evaluates political stance across sentences/paragraphs using fine-tuned BERT.
    Returns probability distribution over left, center, right and continuous score.
    """
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    clf = None
    if not token:
        clf = get_bias_classifier()

    # Split text into chunks (~150 words each) for contextual inference
    words = text.split()
    chunk_size = 150
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    if not chunks:
        chunks = [text]

    left_scores: List[float] = []
    center_scores: List[float] = []
    right_scores: List[float] = []

    for chunk in chunks[:1]:  # Analyze lead headline & context chunk for instant sub-second inference
        if not chunk.strip():
            continue
        try:
            items = _query_hf_inference_bias(chunk)
            if not items:
                if clf is None:
                    clf = get_bias_classifier()
                if clf:
                    with inference_slot():
                        raw_res = clf(chunk)
                    items = raw_res[0] if isinstance(raw_res[0], list) else raw_res

            if items:
                probs = {item["label"].lower(): item["score"] for item in items}
                left_scores.append(probs.get("left", 0.0))
                center_scores.append(probs.get("center", 0.0))
                right_scores.append(probs.get("right", 0.0))
        except Exception as e:
            logger.warning("Stance classification chunk error: %s", e)

    if not left_scores:
        return {
            "probabilities": {"left": 0.33, "center": 0.34, "right": 0.33},
            "stance_score": 0.0,
            "stance_label": "Center"
        }

    avg_left = sum(left_scores) / len(left_scores)
    avg_center = sum(center_scores) / len(center_scores)
    avg_right = sum(right_scores) / len(right_scores)

    # Normalize probabilities
    total = avg_left + avg_center + avg_right or 1.0
    p_left = round(avg_left / total, 3)
    p_center = round(avg_center / total, 3)
    p_right = round(avg_right / total, 3)

    # Compute raw spectrum score: left = -1.0, right = +1.0, center = 0.0
    stance_score = round((p_right * 1.0) + (p_left * -1.0), 3)

    return {
        "probabilities": {
            "left": p_left,
            "center": p_center,
            "right": p_right
        },
        "stance_score": stance_score,
        "stance_label": score_to_category(stance_score)
    }


def analyze_cross_source_distribution(evidence_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Examines evidence sources retrieved from Brave Search, mapping each domain
    to AllSides ratings to compute coverage balance across ideological clusters.
    """
    distribution = {"Left": 0, "Lean Left": 0, "Center": 0, "Lean Right": 0, "Right": 0, "Unrated": 0}
    labeled_sources = []

    for src in evidence_sources:
        url = src.get("url", "")
        domain = extract_domain(url)
        bias_info = lookup_domain_bias(url) if url else None

        if bias_info:
            category = bias_info.get("bias", "Unrated")
            distribution[category] = distribution.get(category, 0) + 1
            labeled_sources.append({
                "title": src.get("title", ""),
                "url": url,
                "domain": domain,
                "outlet": bias_info.get("name", domain),
                "bias": category,
                "score": bias_info.get("score", 0.0)
            })
        elif domain:
            distribution["Unrated"] += 1
            labeled_sources.append({
                "title": src.get("title", ""),
                "url": url,
                "domain": domain,
                "outlet": domain,
                "bias": "Unrated",
                "score": None
            })

    total_rated = sum(distribution[k] for k in ["Left", "Lean Left", "Center", "Lean Right", "Right"])
    
    return {
        "distribution": distribution,
        "total_sources": len(evidence_sources),
        "total_rated": total_rated,
        "sources": labeled_sources
    }


def analyze_bias(
    text: str,
    source_url: Optional[str] = None,
    evidence_sources: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Full-pipeline Political Bias & Framing Analysis.
    Combines:
    - Domain AllSides rating (if URL provided)
    - NLP linguistic stance probabilities (Left/Center/Right)
    - Loaded language density
    - Cross-source coverage distribution
    """
    # 1. Linguistic Stance
    stance_data = classify_text_stance(text)

    # 2. Loaded Language
    loaded_data = analyze_loaded_language(text)

    # 3. Domain Grounding
    domain_bias = None
    # If text starts with a URL, treat it as source_url
    first_token = text.strip().split()[0] if text.strip() else ""
    detected_url = source_url or (first_token if first_token.startswith(("http://", "https://")) else None)
    if detected_url:
        domain_bias = lookup_domain_bias(detected_url)

    # 4. Cross-source analysis from verification evidence
    cross_source = None
    if evidence_sources:
        cross_source = analyze_cross_source_distribution(evidence_sources)

    # 5. Synthesize unified spectrum score (-1.0 Far Left to +1.0 Far Right)
    nlp_score = stance_data["stance_score"]
    
    if domain_bias and "score" in domain_bias:
        # Weighted blend: 60% publisher track-record, 40% specific article text
        final_score = round(0.6 * domain_bias["score"] + 0.4 * nlp_score, 3)
        confidence = 0.90
    else:
        final_score = nlp_score
        confidence = round(max(stance_data["probabilities"].values()), 2)

    final_category = score_to_category(final_score)

    return {
        "bias_label": final_category,
        "spectrum_score": final_score,  # -1.0 to +1.0
        "confidence": confidence,
        "stance": stance_data,
        "domain_rating": domain_bias,
        "loaded_language": loaded_data,
        "cross_source": cross_source
    }
