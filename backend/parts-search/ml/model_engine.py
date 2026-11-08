import json
from ml.improved_retrieval import HybridPartsRetriever

class Engine:
    """Model engine wrapper for HybridPartsRetriever with Engine interface."""

    def __init__(self, catalog_path: str):
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        self.catalog = catalog
        self.retriever = HybridPartsRetriever(catalog)
        # map sku to description for output
        self.sku_to_desc = {p['sku']: p.get('description', '') for p in catalog}

    def search(self, query: str):
        if not query or not query.strip():
            return []
        results = self.retriever.search(query, limit=5)
        out = []
        for r in results:
            sku = r['sku']
            score = float(r.get('score', 0.0))
            # evidence is dict, convert to list of strings
            ev = r.get('evidence', {})
            evidence_list = []
            if isinstance(ev, dict):
                for k, v in ev.items():
                    evidence_list.append(f"{k}: {v}")
            else:
                evidence_list = [str(ev)]
            out.append({
                'sku': sku,
                'description': self.sku_to_desc.get(sku, ''),
                'score': round(score, 4),
                'evidence': evidence_list
            })
        return out
