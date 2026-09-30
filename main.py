# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from claim_extractor import extract_claims
from verifier import verify_claim
from scorer import compute_score
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArticleInput(BaseModel):
    text: str

@app.post("/analyze")
def analyze(article: ArticleInput):
    claims = extract_claims(article.text)
    results = [verify_claim(c) for c in claims[:5]]  # cap at 5 for speed
    score = compute_score(results)
    return {
        "credibility_score": score,
        "claims": results
    }