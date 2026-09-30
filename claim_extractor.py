# claim_extractor.py
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_claims(text: str) -> list[str]:
    doc = nlp(text)
    claims = []
    for sent in doc.sents:
        has_entity = any(ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "PERCENT", "MONEY"] 
                         for ent in sent.ents)
        is_declarative = not sent.text.strip().endswith("?")
        if has_entity and is_declarative:
            claims.append(sent.text.strip())
    return claims