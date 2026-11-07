"""Normalized, hybrid, attribute-aware retrieval for catalog queries."""

import re
from dataclasses import dataclass
from typing import Any

import numpy as np
from rapidfuzz import process
from rapidfuzz.fuzz import ratio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize as l2_normalize
from sklearn.decomposition import TruncatedSVD

from src.baseline import PartsBaseline, tokenize


UNIT_REPLACEMENTS = {
    r"\bmillimeters?\b": " mm",
    r"\bcentimeters?\b": " cm",
    r"\binches?\b": " inch",
}
ABBREVIATIONS = {
    "alu": "aluminum",
    "brg": "bearing",
    "brkt": "bracket",
    "conn": "connector",
    "ss": "stainless steel",
    "stl": "steel",
    "wshr": "washer",
}
FRACTIONS = {"1/4-20": "1/4-20", "1/420": "1/4-20", "3/8-16": "3/8-16", "3816": "3/8-16"}
VOCABULARY = (
    "aluminum", "bearing", "black", "bracket", "brass", "connector", "finish",
    "m6", "m8", "m10", "m12", "nickel", "plain", "seal", "screw", "steel",
    "stainless", "washer", "zinc",
)


def normalize_query(query: str) -> str:
    """Canonicalize units, fractions, abbreviations, and common separators."""
    normalized = query.lower().strip()
    for pattern, replacement in UNIT_REPLACEMENTS.items():
        normalized = re.sub(pattern, replacement, normalized)
    for source, target in ABBREVIATIONS.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    for source, target in FRACTIONS.items():
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"(?<=\d)\s*mm\b", " mm", normalized)
    words = []
    for word in normalized.split():
        match = process.extractOne(word, VOCABULARY, score_cutoff=78)
        words.append(match[0] if match and len(word) >= 4 else word)
    normalized = " ".join(words)
    return re.sub(r"\s+", " ", normalized).strip()


@dataclass(frozen=True)
class ExtractedAttributes:
    values: dict[str, str]
    missing: tuple[str, ...]


class AttributeExtractor:
    """Extract catalog attributes that can constrain candidate ranking."""

    fields = ("material", "thread", "finish", "brand", "category", "length_mm")

    def extract(self, query: str) -> ExtractedAttributes:
        normalized = normalize_query(query)
        values: dict[str, str] = {}
        for field in self.fields:
            if field == "length_mm":
                match = re.search(r"\b(\d+)\s*mm\b", normalized)
                if match:
                    values[field] = match.group(1)
            elif field == "thread":
                match = re.search(r"\b(?:m\d+|\d+/\d+-\d+)\b", normalized)
                if match:
                    values[field] = match.group(0)
            else:
                options = {
                    "material": ("stainless steel", "aluminum", "steel", "brass"),
                    "finish": ("zinc", "black oxide", "plain", "nickel"),
                    "brand": ("forgepro", "northstar", "apex", "mekanix", "rivetworks"),
                    "category": ("bolt", "nut", "washer", "screw", "bearing", "seal", "bracket", "connector"),
                }[field]
                found = next((option for option in options if option in normalized), None)
                if found:
                    values[field] = found
        return ExtractedAttributes(
            values=values,
            missing=tuple(field for field in self.fields if field not in values),
        )


class HybridPartsRetriever:
    """Combine lexical retrieval with dense TF-IDF projection embeddings."""

    def __init__(self, catalog: list[dict[str, str]]) -> None:
        self.baseline = PartsBaseline(catalog)
        self.catalog = catalog
        self.extractor = AttributeExtractor()
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize,
            token_pattern=None,
            lowercase=False,
            ngram_range=(1, 2),
        )
        tfidf_matrix = self.vectorizer.fit_transform(self.baseline.documents)
        component_count = min(64, max(1, tfidf_matrix.shape[1] - 1))
        self.embedding_model = TruncatedSVD(
            n_components=component_count, random_state=20261105
        )
        self.document_matrix = l2_normalize(
            self.embedding_model.fit_transform(tfidf_matrix)
        )

    def _attribute_score(
        self, attributes: ExtractedAttributes, row: dict[str, str]
    ) -> float:
        if not attributes.values:
            return 0.0
        matches = sum(
            str(row.get(field, "")).lower() == value.lower()
            for field, value in attributes.values.items()
        )
        return matches / len(attributes.values)

    def search(self, query: str, limit: int = 5, candidate_limit: int = 50) -> list[dict[str, Any]]:
        normalized = normalize_query(query)
        attributes = self.extractor.extract(normalized)
        lexical = self.baseline.search(normalized, limit=min(candidate_limit, len(self.catalog)))
        candidate_indices = [next(i for i, row in enumerate(self.catalog) if row["sku"] == result["sku"]) for result in lexical]
        query_vector = self.vectorizer.transform([normalized])
        query_embedding = l2_normalize(self.embedding_model.transform(query_vector))
        dense_scores = cosine_similarity(query_embedding, self.document_matrix).ravel()
        reranked = []
        for index in candidate_indices:
            attribute_score = self._attribute_score(attributes, self.catalog[index])
            fuzzy_score = ratio(normalized, self.baseline.documents[index]) / 100
            score = (
                0.45 * dense_scores[index]
                + 0.25 * fuzzy_score
                + 0.30 * attribute_score
            )
            reranked.append((score, index, attribute_score))
        reranked.sort(key=lambda item: (-item[0], self.catalog[item[1]]["sku"]))
        return [
            {
                "sku": self.catalog[index]["sku"],
                "score": round(float(score), 6),
                "evidence": {
                    "normalized_query": normalized,
                    "attributes": attributes.values,
                    "attribute_agreement": round(attribute_score, 4),
                },
            }
            for score, index, attribute_score in reranked[:limit]
        ]
