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
import threading
import html
import re
from typing import Dict, Any, List, Optional
import requests

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from search_provider import fetch_web_evidence, get_search_provider
from bias_detector import evaluate_claim_framing
from xai_explainer import explain_verification
from model_runtime import pipeline_options, inference_slot
from article_identity import same_article_url
from verification_logic import probabilities, eligibility, aggregate, add_influence, trace_explanation

logger = logging.getLogger("BeyondBinary.Verifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Thread-safe lazy loading locks for embedding and NLI models
_embedder_lock = threading.Lock()
_nli_lock = threading.Lock()
_embedder = None
_nli = None

def get_embedder():
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                logger.info("Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
                _embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _embedder

def get_nli():
    global _nli
    if _nli is None:
        with _nli_lock:
            if _nli is None:
                logger.info("Initializing RoBERTa NLI pipeline (roberta-large-mnli)...")
                try:
                    import torch
                    _nli = pipeline(
                        "text-classification",
                        model="roberta-large-mnli",
                        **pipeline_options()
                    )
                except Exception as e:
                    logger.warning("Preferred NLI runtime failed; using CPU: %s", e)
                    _nli = pipeline("text-classification", model="roberta-large-mnli", device=-1, low_cpu_mem_usage=True)
                logger.info("RoBERTa NLI ready on %s", _nli.device)
    return _nli

# Relative path loading for FAISS index and passages
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
index_path = os.path.join(BASE_DIR, "data", "fever_index.faiss")
passages_json_path = os.path.join(BASE_DIR, "data", "passages.json")
passages_pkl_path = os.path.join(BASE_DIR, "data", "passages.pkl")

index = faiss.read_index(index_path)
if os.path.exists(passages_json_path):
    import json
    with open(passages_json_path, "r", encoding="utf-8") as f:
        passages = json.load(f)
elif os.path.exists(passages_pkl_path):
    with open(passages_pkl_path, "rb") as f:
        passages = pickle.load(f)
else:
    passages = []

LABEL_MAP = {
    "ENTAILMENT": "Supported",
    "CONTRADICTION": "Refuted",
    "NEUTRAL": "Not Enough Info"
}


_HF_NLI_AVAILABLE = True

def _query_hf_inference_nli(premise: str, hypothesis: str) -> Optional[Dict[str, Any]]:
    """Query Hugging Face Serverless Inference API for RoBERTa-large-MNLI with fast circuit breaker."""
    global _HF_NLI_AVAILABLE
    if not _HF_NLI_AVAILABLE:
        return None

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        return None
    try:
        url = "https://router.huggingface.co/hf-inference/models/roberta-large-mnli"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": f"{premise}</s></s>{hypothesis}",
            "options": {"wait_for_model": False}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                items = data[0] if isinstance(data[0], list) else data
                items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
                top = items[0]
                return {"label": top["label"], "score": float(top["score"]), "probabilities": probabilities(items)}
        else:
            logger.info("HF Inference API status %d. Tripping circuit breaker to local CPU engine.", resp.status_code)
            _HF_NLI_AVAILABLE = False
    except Exception as e:
        logger.warning("HF Serverless Inference API request failed: %s", e)
        _HF_NLI_AVAILABLE = False
    return None


def _select_sentence(claim: str, text: str):
    """Select a real source sentence; never synthesize a premise from other outlets."""
    from claim_extractor import get_nlp
    clean = html.unescape(text).strip()
    candidates = list(dict.fromkeys(sent.text.strip() for sent in get_nlp()(clean).sents
                                    if len(sent.text.strip().split()) >= 4))[:40]
    candidates = candidates or [clean]
    vectors = get_embedder().encode([claim] + candidates, normalize_embeddings=True,
                                   show_progress_bar=False)
    similarities = vectors[1:] @ vectors[0]
    chosen = int(np.argmax(similarities))
    return candidates[chosen], float(similarities[chosen])


def verify_claim(claim: str, source_url: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve evidence, retain full NLI vectors, and abstain on weak/conflicting evidence."""
    embedding = get_embedder().encode([claim]).astype("float32")
    distances, indices = index.search(embedding, k=2)
    dist_val = float(distances[0][0])
    evidence, sources = [], []
    retrieval_source = "Local FAISS Index"
    if dist_val > 0.70:
        evidence, sources = fetch_web_evidence(claim, max_results=3)
        if evidence:
            retrieval_source = f"{sources[0].get('source_type', 'Live Web Search') if sources else 'Live Web Search'} (Live Corroboration)"
    if not evidence and dist_val <= 0.85:
        for i in indices[0]:
            if 0 <= i < len(passages):
                evidence.append(passages[i])
                sources.append({'title': f'Local Wiki Corpus #{i}', 'url': '',
                                'snippet': passages[i], 'source_type': 'Local FAISS Index'})
    if not evidence:
        retrieval_source = 'Unverified (Insufficient Corroboration)'

    rows, seen_text, seen_urls = [], set(), set()
    for position, text in enumerate(evidence[:3]):
        source = sources[position] if position < len(sources) else {'title': 'Retrieved passage', 'url': ''}
        row = {'id': f'E{position + 1}', 'source': source, 'sentence': html.unescape(text),
               'eligible': False, 'probabilities': None, 'similarity': None}
        try:
            sentence, similarity = _select_sentence(claim, text)
            row.update(sentence=sentence, similarity=round(similarity, 4))
            fingerprint = ' '.join(re.findall(r'\w+', sentence.lower()))
            url = source.get('url', '')
            duplicate = fingerprint in seen_text or (url and any(same_article_url(url, previous) for previous in seen_urls))
            eligible, reason = eligibility(claim, sentence, similarity,
                same_source=bool(source_url and url and same_article_url(source_url, url)), duplicate=bool(duplicate))
            row.update(eligible=eligible, eligibility_reason=reason)
            if eligible:
                seen_text.add(fingerprint)
                if url:
                    seen_urls.add(url)
            # Scores remain visible even when a passage is ineligible for the verdict.
            api_result = _query_hf_inference_nli(sentence, claim)
            if api_result:
                raw = api_result
            else:
                nli = get_nli()
                with inference_slot():
                    raw = nli({'text': sentence, 'text_pair': claim}, top_k=None,
                              truncation=True, max_length=256)
            row['probabilities'] = probabilities(raw)
        except Exception as error:
            logger.warning('Evidence %s could not be evaluated: %s', row['id'], error)
            row.update(eligible=False, eligibility_reason='The inference step could not evaluate this passage.')
        rows.append(row)

    verdict, confidence, reason = aggregate(rows)
    most_influential = add_influence(rows)
    framing = evaluate_claim_framing(claim, [], [row['sentence'] for row in rows])
    explanation = trace_explanation(verdict, reason, rows)
    explanation['flagged_markers'] = framing.get('detected_markers', [])
    # Put the strongest relevant decision evidence first for existing readers.
    label = 'entailment' if verdict == 'Supported' else 'contradiction'
    ordered = sorted(rows, key=lambda row: (
        bool(row.get('eligible')), (row.get('probabilities') or {}).get(label, 0)), reverse=True)
    return {
        'claim': claim, 'verdict': verdict, 'confidence': confidence,
        'confidence_kind': 'NLI model score; not calibrated factual accuracy',
        'evidence': [row['sentence'] for row in ordered],
        'sources': [row['source'] for row in ordered],
        'retrieval_source': retrieval_source, 'framing_analysis': framing,
        'xai_rationale': explanation, 'evidence_trace': rows,
        'decision': {'reason': reason, 'most_influential_evidence': most_influential,
                     'evaluated_count': sum(row['probabilities'] is not None for row in rows),
                     'eligible_count': sum(row['eligible'] for row in rows),
                     'method': 'Eligible entailment/contradiction >= 0.72; opposing decisive evidence yields Not Enough Info. Influence removes one passage without new retrieval.'},
    }
