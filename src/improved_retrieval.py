import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
VOCABULARY = (
    "aluminum", "bearing", "black", "bracket", "brass", "connector", "finish",
    "m6", "m8", "m10", "m12", "nickel", "plain", "seal", "screw", "steel",
    "stainless", "washer", "zinc",
)
INSTRUCTION_PATTERNS = (
    r"\b(ignore|disregard|forget)\b.{0,40}\b(instruction|prompt|rule)s?\b",
    r"\b(system|developer|assistant)\s*:",
    r"\b(reveal|show|print)\b.{0,30}\b(prompt|secret|instruction)s?\b",
)
ATTRIBUTE_OPTIONS = {
    "material": ("stainless steel", "aluminum", "steel", "brass"),
    "finish": ("zinc", "black oxide", "plain", "nickel"),
    "brand": ("forgepro", "northstar", "apex", "mekanix", "rivetworks"),
    "category": (
        "bolt",
        "nut",
        "washer",
        "screw",
        "bearing",
        "seal",
        "bracket",
        "connector",
    ),
}


def replace_terms(query: str, replacements: dict[str, str]) -> str:
    for source, target in replacements.items():
        query = re.sub(rf"\b{re.escape(source)}\b", target, query)
    return query


def correct_vocabulary(query: str) -> str:
    words = []
    for word in query.split():
        match = process.extractOne(word, VOCABULARY, score_cutoff=78)
        words.append(match[0] if match and len(word) >= 4 else word)
    return " ".join(words)


def detect_prompt_injection(query: str) -> bool:
    return any(re.search(pattern, query, flags=re.IGNORECASE) for pattern in INSTRUCTION_PATTERNS)


def normalize_query(query: str) -> str:
    normalized = query.lower().strip()
    for pattern, replacement in UNIT_REPLACEMENTS.items():
        normalized = re.sub(pattern, replacement, normalized)
    normalized = replace_terms(normalized, ABBREVIATIONS)
    normalized = normalized.replace("1/420", "1/4-20").replace("3816", "3/8-16")
    normalized = re.sub(r"(?<=\d)\s*mm\b", " mm", normalized)
    return re.sub(r"\s+", " ", correct_vocabulary(normalized)).strip()


@dataclass(frozen=True)
class ExtractedAttributes:
    values: dict[str, str]
    missing: tuple[str, ...]


class AttributeExtractor:
    fields = ("material", "thread", "finish", "brand", "category", "length_mm")

    @staticmethod
    def find_value(query: str, field: str) -> str | None:
        if field == "length_mm":
            match = re.search(r"\b(\d+)\s*mm\b", query)
            return match.group(1) if match else None
        if field == "thread":
            match = re.search(r"\b(?:m\d+|\d+/\d+-\d+)\b", query)
            return match.group(0) if match else None
        return next(
            (option for option in ATTRIBUTE_OPTIONS[field] if option in query),
            None,
        )

    def extract(self, query: str) -> ExtractedAttributes:
        normalized = normalize_query(query)
        values = {
            field: value
            for field in self.fields
            if (value := self.find_value(normalized, field)) is not None
        }
        return ExtractedAttributes(
            values=values,
            missing=tuple(field for field in self.fields if field not in values),
        )


class HybridPartsRetriever:
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
        self.calibrator: Any | None = None

    @classmethod
    def from_csv(cls, path: str | Path) -> "HybridPartsRetriever":
        with Path(path).open(encoding="utf-8", newline="") as file:
            return cls(list(csv.DictReader(file)))

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

    def _candidate_indices(self, query: str, candidate_limit: int) -> list[int]:
        lexical = self.baseline.search(
            query, limit=min(candidate_limit, len(self.catalog))
        )
        index_by_sku = {row["sku"]: i for i, row in enumerate(self.catalog)}
        return [index_by_sku[result["sku"]] for result in lexical]

    def _candidate_scores(
        self,
        normalized: str,
        attributes: ExtractedAttributes,
        candidate_indices: list[int],
    ) -> list[tuple[float, int, float]]:
        query_vector = self.vectorizer.transform([normalized])
        query_embedding = l2_normalize(self.embedding_model.transform(query_vector))
        dense_scores = cosine_similarity(query_embedding, self.document_matrix).ravel()
        return [
            (
                0.45 * dense_scores[index]
                + 0.25 * ratio(normalized, self.baseline.documents[index]) / 100
                + 0.30 * self._attribute_score(attributes, self.catalog[index]),
                index,
                self._attribute_score(attributes, self.catalog[index]),
            )
            for index in candidate_indices
        ]

    def _result(
        self,
        score: float,
        index: int,
        attribute_score: float,
        normalized: str,
        attributes: ExtractedAttributes,
    ) -> dict[str, Any]:
        return {
            "sku": self.catalog[index]["sku"],
            "score": float(score),
            "evidence": {
                "normalized_query": normalized,
                "attributes": attributes.values,
                "attribute_agreement": round(attribute_score, 4),
            },
        }

    def _catalog_row(self, sku: str) -> dict[str, str]:
        return next(row for row in self.catalog if row["sku"] == sku)

    def _explanation(self, sku: str) -> str:
        row = self._catalog_row(sku)
        details = (
            f"{row['description']} by {row['brand']}; "
            f"category={row['category']}, material={row['material']}, "
            f"thread={row['thread']}, length_mm={row['length_mm']}, "
            f"finish={row['finish']}."
        )
        return f"Catalog-grounded match for {row['sku']}: {details}"

    @staticmethod
    def _add_confidence(results: list[dict[str, Any]]) -> None:
        if not results:
            return
        top_score = results[0]["score"]
        second_score = results[1]["score"] if len(results) > 1 else 0.0
        margin = max(0.0, min(1.0, (top_score - second_score) * 10))
        agreement = results[0]["evidence"]["attribute_agreement"]
        results[0]["confidence"] = round(
            max(0.0, min(1.0, 0.5 * top_score + 0.25 * margin + 0.25 * agreement)),
            6,
        )
        results[0]["evidence"]["score_margin"] = round(top_score - second_score, 6)

    def _rank(
        self, query: str, limit: int, candidate_limit: int
    ) -> list[dict[str, Any]]:
        normalized = normalize_query(query)
        attributes = self.extractor.extract(normalized)
        candidate_indices = self._candidate_indices(normalized, candidate_limit)
        reranked = self._candidate_scores(normalized, attributes, candidate_indices)
        reranked.sort(key=lambda item: (-item[0], self.catalog[item[1]]["sku"]))
        ranked_results = [
            self._result(score, index, attribute_score, normalized, attributes)
            for score, index, attribute_score in reranked[:limit]
        ]
        self._add_confidence(ranked_results)
        self._add_calibrated_confidence(ranked_results)
        return ranked_results

    def _add_calibrated_confidence(self, results: list[dict[str, Any]]) -> None:
        if results and self.calibrator is not None:
            results[0]["calibrated_confidence"] = round(
                float(self.calibrator.predict([results[0]["confidence"]])[0]), 6
            )

    def search(
        self,
        query: str,
        limit: int = 5,
        candidate_limit: int = 50,
        include_explanation: bool = False,
    ) -> list[dict[str, Any]]:
        self._validate_search(query, limit)
        results = self._rank(query, limit, candidate_limit)
        catalog_skus = {row["sku"] for row in self.catalog}
        grounded = [result for result in results if result["sku"] in catalog_skus]
        injection_detected = detect_prompt_injection(query)
        for result in grounded:
            result["evidence"]["catalog_verified"] = True
            result["evidence"]["prompt_injection_detected"] = injection_detected
            if include_explanation:
                result["explanation"] = self._explanation(result["sku"])
        return grounded

    def search_or_not_found(
        self,
        query: str,
        limit: int = 5,
        min_confidence: float = 0.9,
    ) -> dict[str, Any]:
        results = self.search(query, limit=limit)
        confidence = results[0]["confidence"] if results else 0.0
        if not results or confidence < min_confidence:
            return {
                "status": "not_found",
                "query": query,
                "results": [],
                "reason": "No sufficiently confident catalog match",
            }
        return {"status": "found", "query": query, "results": results}

    @staticmethod
    def _validate_search(query: str, limit: int) -> None:
        if not query.strip():
            raise ValueError("Query must not be empty")
        if limit < 1:
            raise ValueError("Limit must be positive")
