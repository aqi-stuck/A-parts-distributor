def keyword_fallback(catalog: list[dict], query: str, limit: int = 5):
    """Simple keyword fallback search over catalog."""
    if not query or not query.strip():
        return []
    words = query.lower().split()
    if not words:
        return []
    results = []
    n_words = len(words)
    for part in catalog:
        text = ' '.join([
            part.get('description', ''),
            part.get('brand', ''),
            part.get('size', ''),
            part.get('material', ''),
            part.get('category', '')
        ]).lower()
        matched = [w for w in words if w in text]
        if not matched:
            continue
        score = len(matched) / n_words
        results.append({
            "sku": part['sku'],
            "description": part['description'],
            "score": round(score, 4),
            "evidence": [f"matched: {w}" for w in matched]
        })
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]
