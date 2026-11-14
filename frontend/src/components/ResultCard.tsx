import type { SearchResult } from "../api";
import { EvidencePanel } from "../components/EvidencePanel";

export function ResultCard({
  result,
  isTopResult,
}: {
  result: SearchResult;
  isTopResult: boolean;
  saving: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <article className="result">
      <div className="result-header">
        <div>
          <h3>{result.sku}</h3>
          <p className="result-description">{result.description}</p>
        </div>
        {isTopResult && (
          <div className="result-confidence">
            {result.confidence > 0
              ? `${Math.round(Math.min(1, Math.max(0, result.confidence)) * 100)}% confidence`
              : "Confidence unavailable"}
          </div>
        )}
      </div>

      <EvidencePanel result={result} />
    </article>
  );
}