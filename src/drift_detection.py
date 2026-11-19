from collections import Counter
from typing import Any

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics.pairwise import cosine_similarity

from src.improved_retrieval import HybridPartsRetriever, normalize_query
from src.baseline import tokenize


class DriftDetector:

    def __init__(
        self,
        retriever: HybridPartsRetriever,
        reference_queries: list[str],
        threshold_quantile: float = 0.95,
    ) -> None:
        if not reference_queries:
            raise ValueError("Reference queries must not be empty")
        self.retriever = retriever
        self.reference_queries = reference_queries
        self.known_tokens = set(retriever.vectorizer.vocabulary_)
        self.known_categories = {
            row["category"].lower() for row in retriever.catalog if row.get("category")
        }
        self.reference_features = [
            self.features(query) for query in reference_queries
        ]
        reference_scores = np.asarray(
            [self._score_features(features) for features in self.reference_features]
        )
        self.threshold = float(np.quantile(reference_scores, threshold_quantile))

    def features(self, query: str) -> dict[str, Any]:
        normalized = normalize_query(query)
        tokens = tokenize(normalized)
        unseen_rate = (
            sum(token not in self.known_tokens for token in tokens) / len(tokens)
            if tokens
            else 1.0
        )
        query_vector = self.retriever.vectorizer.transform([normalized])
        query_embedding = self.retriever.embedding_model.transform(query_vector)
        similarities = cosine_similarity(
            query_embedding, self.retriever.document_matrix
        ).ravel()
        category = next(
            (value for value in self.known_categories if value in normalized),
            "unknown",
        )
        return {
            "embedding_distance": float(1.0 - similarities.max(initial=0.0)),
            "unseen_token_rate": float(unseen_rate),
            "query_length": len(tokens),
            "category": category,
            "unknown_category": float(category == "unknown"),
        }

    @staticmethod
    def _score_features(features: dict[str, Any]) -> float:
        length_signal = min(float(features["query_length"]) / 20.0, 1.0)
        return float(
            0.45 * features["embedding_distance"]
            + 0.30 * features["unseen_token_rate"]
            + 0.15 * length_signal
            + 0.10 * features["unknown_category"]
        )

    def score_query(self, query: str) -> dict[str, Any]:
        features = self.features(query)
        score = self._score_features(features)
        return {
            "query": query,
            "features": features,
            "ood_score": round(score, 6),
            "threshold": round(self.threshold, 6),
            "is_ood": score > self.threshold,
        }

    def _ks_statistics(
        self, reference: list[dict[str, Any]], observed: list[dict[str, Any]]
    ) -> dict[str, float]:
        fields = ("embedding_distance", "unseen_token_rate", "query_length")
        return {
            field: float(
                ks_2samp(
                    [item[field] for item in reference],
                    [item[field] for item in observed],
                ).statistic
            )
            for field in fields
        }

    @staticmethod
    def _population_stability_index(
        reference: list[dict[str, Any]], observed: list[dict[str, Any]]
    ) -> float:
        reference_categories = Counter(item["category"] for item in reference)
        observed_categories = Counter(item["category"] for item in observed)
        categories = set(reference_categories) | set(observed_categories)
        reference_total = len(reference)
        observed_total = len(observed)
        return float(
            sum(
                (
                    max(observed_categories[category] / observed_total, 1e-6)
                    - max(reference_categories[category] / reference_total, 1e-6)
                )
                * np.log(
                    max(observed_categories[category] / observed_total, 1e-6)
                    / max(reference_categories[category] / reference_total, 1e-6)
                )
                for category in categories
            )
        )

    @staticmethod
    def _drift_alert(ks_statistics: dict[str, float], psi: float) -> bool:
        return max(ks_statistics.values()) >= 0.2 or psi >= 0.2

    def window_drift(self, queries: list[str]) -> dict[str, Any]:
        if not queries:
            raise ValueError("Window queries must not be empty")
        current = [self.features(query) for query in queries]
        numeric_tests = self._ks_statistics(self.reference_features, current)
        psi = self._population_stability_index(self.reference_features, current)
        return {
            "queries": len(queries),
            "max_ks_statistic": round(max(numeric_tests.values()), 6),
            "ks_statistics": {key: round(value, 6) for key, value in numeric_tests.items()},
            "population_stability_index": round(float(psi), 6),
            "alert": self._drift_alert(numeric_tests, psi),
        }
