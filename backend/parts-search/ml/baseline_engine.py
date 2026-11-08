import json
from typing import List

class Engine:
    """Loads catalog and performs simple word-match search."""

    def __init__(self, catalog_path: str):
        """Load JSON catalog into memory."""
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = json.load(f)

    def search(self, query: str) -> list[dict]:
        """Return up to 5 matching parts ranked by word match score."""
        if not query or not query.strip():
            return []
        words = query.lower().split()
        if not words:
            return []
        results = []
        n_words = len(words)
        for part in self.catalog:
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
        return results[:5]
