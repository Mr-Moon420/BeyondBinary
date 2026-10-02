# verifier.py
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import faiss, numpy as np, pickle
import urllib.request, json
import urllib.parse

embedder = SentenceTransformer("all-MiniLM-L6-v2")
nli = pipeline("text-classification", model="roberta-large-mnli")

index = faiss.read_index("data/fever_index.faiss")
with open("data/passages.pkl", "rb") as f:
    passages = pickle.load(f)

LABEL_MAP = {
    "ENTAILMENT": "Supported",
    "CONTRADICTION": "Refuted",
    "NEUTRAL": "Not Enough Info"
}

def fetch_wikipedia_evidence(claim: str) -> str:
    import re
    import spacy
    
    clean = " ".join(claim.split())
    
    # Use spaCy to extract the most specific named entity as query
    nlp_local = spacy.load("en_core_web_sm")
    doc = nlp_local(clean)
    
    # Prefer ORG or PERSON entities as search terms — most specific
    entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PERSON", "GPE", "PRODUCT"]]
    
    if entities:
        query = entities[0]  # most prominent named entity
    else:
        query = " ".join(clean.split()[:4])
    
    print(f"WIKIPEDIA QUERY: {query}")
    
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8=1&srlimit=3"
    req = urllib.request.Request(
        search_url,
        headers={"User-Agent": "NewsLens/1.0 (academic project; contact@example.com)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            results = data.get("query", {}).get("search", [])
            if not results:
                print("WIKIPEDIA: no results")
                return ""
            snippets = [re.sub(r'<[^>]+>', '', r.get("snippet", "")) for r in results]
            combined = " ".join(snippets)
            print(f"WIKIPEDIA RESULT: {combined[:100]}")
            return combined[:1000]
    except Exception as e:
        print(f"WIKIPEDIA FAILED: {e}")
        return ""

def verify_claim(claim: str) -> dict:
    embedding = embedder.encode([claim]).astype("float32")
    distances, indices = index.search(embedding, k=2)
    
    print(f"CLAIM: {claim[:60]}")
    print(f"DISTANCES: {distances[0]}")  # debug
    
    if distances[0][0] > 0.8:  # lowered from 1.5
        wiki = fetch_wikipedia_evidence(claim)
        evidence = [wiki] if wiki else [passages[i] for i in indices[0]]
        print("USING WIKIPEDIA FALLBACK")
    else:
        evidence = [passages[i] for i in indices[0]]
        print("USING FAISS")


    verdicts = []
    confidences = []
    for ev in evidence:
        if not ev.strip():
            continue
        result = nli(f"{claim} [SEP] {ev}", truncation=True, max_length=512)
        verdicts.append(result[0]["label"])
        confidences.append(result[0]["score"])

    if not verdicts:
        return {"claim": claim, "verdict": "Not Enough Info", "confidence": 0.5, "evidence": evidence}

    final = max(set(verdicts), key=verdicts.count)
    avg_confidence = round(sum(confidences) / len(confidences), 3)

    return {
        "claim": claim,
        "verdict": LABEL_MAP.get(final, "Not Enough Info"),
        "confidence": avg_confidence,
        "evidence": evidence
    }