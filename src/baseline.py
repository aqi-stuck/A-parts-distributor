import csv
import re
from pathlib import Path
from typing import Any

import numpy as np
from rapidfuzz.fuzz import ratio
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class PartsBaseline:

    def __init__(self, catalog: list[dict[str, str]]) -> None:
        if not catalog:
            raise ValueError("Catalog must contain at least one row")
        self.catalog = catalog
        self.documents = [
            " ".join(
                row.get(field, "")
                for field in (
                    "sku",
                    "description",
                    "brand",
                    "category",
                    "material",
                    "thread",
                    "diameter_mm",
                    "length_mm",
                    "finish",
                    "compatible_model",
                )
            )
            for row in catalog
        ]
        self.tokenized_documents = [tokenize(document) for document in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_documents)
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize,
            token_pattern=None,
            lowercase=False,
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(self.documents)

    @classmethod
    def from_csv(cls, path: str | Path) -> "PartsBaseline":
        with Path(path).open(encoding="utf-8", newline="") as file:
            return cls(list(csv.DictReader(file)))

    @staticmethod
    def _normalize(scores: np.ndarray) -> np.ndarray:
        maximum = float(scores.max(initial=0))
        return scores / maximum if maximum > 0 else np.zeros_like(scores)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Query must not be empty")
        if limit < 1:
            raise ValueError("Limit must be positive")

        bm25_scores = self._normalize(
            np.asarray(self.bm25.get_scores(tokenize(query)), dtype=float)
        )
        tfidf_scores = self._normalize(
            (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()
        )
        fuzzy_scores = np.asarray(
            [
                ratio(query.lower(), row["description"].lower()) / 100
                for row in self.catalog
            ],
            dtype=float,
        )
        scores = 0.45 * bm25_scores + 0.35 * tfidf_scores + 0.20 * fuzzy_scores
        ranked = np.argsort(-scores, kind="stable")[:limit]
        query_tokens = set(tokenize(query))
        results = []
        for index in ranked:
            matched = sorted(query_tokens.intersection(self.tokenized_documents[index]))
            results.append(
                {
                    "sku": self.catalog[index]["sku"],
                    "score": round(float(scores[index]), 6),
                    "evidence": {"matched_tokens": matched},
                }
            )
        return results
