from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="whispAI/ClaimBuster-DeBERTaV2"
)

def extract_claims(text: str) -> list[str]:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 10]
    if not sentences:
        return []
    
    scored = classifier(sentences, truncation=True, max_length=512)
    
    # DEBUG — print everything
    for sent, result in zip(sentences, scored):
        print(f"SENTENCE: {sent}")
        print(f"LABEL: {result['label']} | SCORE: {result['score']:.3f}")
        print()
    
    claims = [
        sent for sent, result in zip(sentences, scored)
        if ("CFS" in result["label"] or "Check-worthy" in result["label"]) and result["score"] > 0.5
    ]
    if not claims and sentences:
        # Fallback: find sentence with highest CFS probability or top sentence
        cfs_candidates = [
            (result["score"] if ("CFS" in result["label"] or "Check-worthy" in result["label"]) else 0.0, sent)
            for sent, result in zip(sentences, scored)
        ]
        cfs_candidates.sort(key=lambda x: x[0], reverse=True)
        claims = [cfs_candidates[0][1]]

    return claims[:5]