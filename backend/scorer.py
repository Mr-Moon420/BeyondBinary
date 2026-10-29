# scorer.py
"""
Credibility scoring module for BeyondBinary.
Computes a calibrated multi-dimensional credibility score based on:
1. Factual veracity of extracted claims verified via NLI entailment.
2. Confidence weighting of each verdict (Supported, NEI, Misleading, Refuted).
3. Mild penalty calibration for highly sensationalized / loaded rhetoric.
"""

from typing import List, Dict, Any

def compute_score(results: List[Dict[str, Any]], loaded_density_pct: float = 0.0) -> float:
    """
    Computes a composite credibility score in range [0.0, 100.0].
    
    Verdicts are weighted as follows:
    - Supported: 1.0 (corroborated by reliable knowledge base or news wires)
    - Not Enough Info: 0.5 (uncontested claim with limited archival corroboration)
    - Misleading-Framing: 0.35 (factual divergence or sensationalized spin detected)
    - Refuted: 0.0 (direct contradiction with authoritative evidence)
    """
    if not results:
        return 0.0

    weights = {
        "Supported": 1.0,
        "Not Enough Info": 0.5,
        "Misleading-Framing": 0.35,
        "Refuted": 0.0
    }

    weighted_sum = sum(weights.get(r.get("verdict"), 0.5) * r.get("confidence", 1.0) for r in results)
    max_possible = sum(r.get("confidence", 1.0) for r in results)

    if max_possible == 0:
        return 0.0

    raw_score = (weighted_sum / max_possible) * 100.0

    # Calibrate with loaded language penalty if severe sensationalism is detected (> 2.5% of vocabulary)
    if loaded_density_pct > 2.5:
        penalty = min(12.0, (loaded_density_pct - 2.5) * 2.0)
        raw_score = max(0.0, raw_score - penalty)

    return round(raw_score, 2)
