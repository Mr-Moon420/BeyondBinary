# verifier.py
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import faiss, numpy as np, pickle

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

def verify_claim(claim: str) -> dict:
    embedding = embedder.encode([claim]).astype("float32")
    _, indices = index.search(embedding, k=3)
    evidence = [passages[i] for i in indices[0]]

    # Run NLI on claim + each evidence passage, take majority
    verdicts = []
    confidences = []
    for ev in evidence:
        result = nli(f"{claim} [SEP] {ev}", truncation=True, max_length=512)
        verdicts.append(result[0]["label"])
        confidences.append(result[0]["score"])

    final = max(set(verdicts), key=verdicts.count)
    avg_confidence = round(sum(confidences) / len(confidences), 3)

    return {
        "claim": claim,
        "verdict": LABEL_MAP.get(final, "Not Enough Info"),
        "confidence": avg_confidence,
        "evidence": evidence
    }