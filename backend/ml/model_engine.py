import json
import threading
from ml.improved_retrieval import HybridPartsRetriever

class Engine:
    """Model engine wrapper for HybridPartsRetriever with Engine interface."""

    def __init__(self, catalog_path: str):
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        self.catalog = catalog
        self._lock = threading.RLock()
        self.retriever = HybridPartsRetriever(catalog)
        self._feedback_aliases: dict[str, str] = {}
        # map sku to description for output
        self.sku_to_desc = {p['sku']: p.get('description', '') for p in catalog}

    def reload_feedback(self, examples: list[tuple[str, str]]) -> None:
        """Rebuild the retriever with approved/corrected query-SKU aliases."""
        augmented_catalog = list(self.catalog)
        aliases_by_sku: dict[str, list[str]] = {}
        feedback_aliases: dict[str, str] = {}
        valid_skus = {str(part["sku"]) for part in self.catalog}
        for query, sku in examples:
            query = query.strip()
            sku = sku.strip()
            if query and sku in valid_skus:
                aliases_by_sku.setdefault(sku, []).append(query)
                feedback_aliases[query.lower()] = sku
        augmented_catalog = [
            {
                **part,
                "description": " ".join(
                    [str(part.get("description", "")).strip()]
                    + list(dict.fromkeys(
                        aliases_by_sku.get(str(part["sku"]), [])
                    ))
                ).strip(),
            }
            if str(part["sku"]) in valid_skus
            else part
            for part in self.catalog
        ]
        with self._lock:
            self.retriever = HybridPartsRetriever(augmented_catalog)
            self._feedback_aliases = feedback_aliases

    def record_feedback(self, query: str, sku: str) -> None:
        """Apply one approved/corrected query-SKU pair immediately."""
        if not query or not sku:
            return
        valid_skus = {str(part["sku"]) for part in self.catalog}
        if sku not in valid_skus:
            return
        with self._lock:
            self._feedback_aliases[query.strip().lower()] = sku
            training_catalog = [
                dict(part) for part in self.retriever.catalog
            ]
            if not query.strip():
                return
            matched = False
            for part in training_catalog:
                if str(part["sku"]) != sku:
                    continue
                description = str(part.get("description", "")).strip()
                alias_terms = [term.strip() for term in description.split() if term.strip()]
                if query.strip().lower() not in description.lower():
                    part["description"] = (
                        f"{description} {query.strip()}".strip()
                    )
                matched = True
                break
            if not matched:
                return
            self.retriever = HybridPartsRetriever(training_catalog)

    def search(self, query: str):
        if not query or not query.strip():
            return []
        with self._lock:
            retriever = self.retriever
            alias_sku = self._feedback_aliases.get(query.strip().lower())
        if alias_sku:
            return [{
                "sku": alias_sku,
                "description": self.sku_to_desc.get(alias_sku, ""),
                "score": 1.0,
                "confidence": 1.0,
                "evidence": ["matched human-reviewed query"],
            }]
        results = retriever.search(query, limit=5)
        out = []
        for r in results:
            sku = r['sku']
            score = float(r.get('score', 0.0))
            # evidence is dict, convert to list of strings
            ev = r.get('evidence', {})
            evidence_list = []
            if isinstance(ev, dict):
                for key, status in (
                    ("matched_attributes", "matched"),
                    ("missing_attributes", "different"),
                ):
                    for field, value in ev.get(key, {}).items():
                        evidence_list.append(f"{status} attribute: {field} = {value}")
                evidence_list.extend(
                    f"not specified: {field}"
                    for field in ev.get("unspecified_attributes", ())
                )
            else:
                evidence_list = [str(ev)]
            out.append({
                'sku': sku,
                'description': self.sku_to_desc.get(sku, ''),
                'score': round(score, 4),
                'confidence': round(float(r.get('confidence', score)), 4),
                'evidence': evidence_list
            })
        return out
