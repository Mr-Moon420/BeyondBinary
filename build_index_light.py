# build_index_light.py
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle, os

os.makedirs("data", exist_ok=True)

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading dataset...")

#Currently not using the full FEVER dataset due to size constraints. Using a smaller dataset for demonstration.
dataset = load_dataset("sentence-transformers/wikipedia-en-sentences", split="train[:10000]")

passages = [row["sentence"] for row in dataset if row["sentence"].strip()]

print(f"Encoding {len(passages)} passages...")
embeddings = model.encode(passages, batch_size=32, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, "data/fever_index.faiss")
with open("data/passages.pkl", "wb") as f:
    pickle.dump(passages, f)

print("Done. Index saved to data/")