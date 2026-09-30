def compute_score(results: list[dict]) -> float:
    if not results:
        return 0.0
    weights = {"Supported": 1.0, "Not Enough Info": 0.5, "Refuted": 0.0}
    total = sum(weights[r["verdict"]] * r.get("confidence", 1.0) for r in results)
    max_possible = sum(r.get("confidence", 1.0) for r in results)
    return round((total / max_possible) * 100, 2)