# Simple search engine for parts catalog

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
                part.get('description',''),
                part.get('brand',''),
                part.get('size',''),
                part.get('material',''),
                part.get('category','')
            ]).lower()
            matched = []
            for w in words:
                if w in text:
                    matched.append(w)
            match_count = len(matched)
            if match_count == 0:
                continue
            score = match_count / n_words
            evidence = [f"matched: {w}" for w in matched]
            results.append({
                "sku": part['sku'],
                "description": part['description'],
                "score": round(score, 4),
                "evidence": evidence
            })
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]
