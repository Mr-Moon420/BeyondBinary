# scripts/build_index.py
"""
Offline FAISS Index Generator for BeyondBinary.
Encodes Wikipedia/FEVER reference sentences with SentenceTransformer (all-MiniLM-L6-v2)
and builds a local L2 distance FAISS index for high-speed semantic retrieval.
"""

import os
import pickle
import numpy as np
import faiss
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

# Resolve project data directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

INDEX_PATH = os.path.join(DATA_DIR, "fever_index.faiss")
PASSAGES_PATH = os.path.join(DATA_DIR, "passages.pkl")

print(f"Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading Wikipedia reference corpus split train[:10000]...")
dataset = load_dataset("sentence-transformers/wikipedia-en-sentences", split="train[:10000]")

passages = [row["sentence"] for row in dataset if row["sentence"].strip()]
print(f"Encoding {len(passages)} passages into 384-dimensional embeddings...")
embeddings = model.encode(passages, batch_size=32, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

print("Constructing FAISS IndexFlatL2...")
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, INDEX_PATH)
with open(PASSAGES_PATH, "wb") as f:
    pickle.dump(passages, f)

print(f"Done! Successfully generated index at: {INDEX_PATH}")
