import { useMemo, useState } from "react";
import { search, feedback } from "../api";
import type { SearchResponse, SearchResult } from "../api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const doSearch = async () => {
    const q = query.trim();
    if (!q) {
      setError("Enter a part description before searching.");
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);
    setLastQuery(q);

    try {
      const res = await search(q);
      setData(res);
    } catch {
      setError("Could not reach the search service. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const onApproveReject = async (sku: string, decision: "approve" | "reject") => {
    try {
      setSavingId(sku);
      await feedback(lastQuery || query, sku, decision);
    } catch {
      setError("Failed to save your review decision.");
    } finally {
      setSavingId(null);
    }
  };

  const summary = useMemo(() => {
    if (!data || data.results.length === 0) return null;
    return data.results[0];
  }, [data]);

  return (
    <section className="card w-full">
      <div className="page-header">
        <h2 className="eyebrow">Warehouse lookup</h2>
      </div>

      <div className="input-row">
        <input
          id="part-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. m8 zinc hex bolt 50 mm"
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          aria-label="Part description"
        />
        <button onClick={doSearch} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      {/* <p className="helper">Press Enter to run a lookup</p> */}

      {loading && <div className="status-box">Searching catalog...</div>}
      {error && (
        <div className="banner error">
          {error}
          <button onClick={doSearch} className="secondary-button">
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          <div className="status-row">
            <span className={`badge ${data.route}`}>
              {data.route === "auto" ? "Auto answer" : "Needs review"}
            </span>
            {data.route === "review" && data.reason && (
              <span className="reason-pill">{data.reason}</span>
            )}
          </div>

          {summary && (
            <div className="summary-card">
              <h3>BEST MATCH</h3>
              <div className="summary-topline">
                <span className="summary-sku">{summary.sku}</span>
                <span className="summary-score">{Math.round(summary.score * 100)}% confidence</span>
              </div>
              <p>{summary.description}</p>
            </div>
          )}

          {data.results.length === 0 ? (
            <p className="empty-state">No matching parts found. This request should be sent to a human reviewer.</p>
          ) : (
            data.results.map((r: SearchResult) => (
              <ResultCard
                key={r.sku}
                result={r}
                route={data.route}
                saving={savingId === r.sku}
                onApprove={() => onApproveReject(r.sku, "approve")}
                onReject={() => onApproveReject(r.sku, "reject")}
              />
            ))
          )}

          <div className="footer-row">
            <div className="footer">Answered in {data.latency_ms} ms</div>
            {data.timing_ms && (
              <div className="footer subtle">
                engine {data.timing_ms.engine} ms · routing {data.timing_ms.routing} ms
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function ResultCard({
  result,
  route,
  saving,
  onApprove,
  onReject,
}: {
  result: SearchResult;
  route: "auto" | "review";
  saving: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const pct = Math.round(result.score * 100);
  return (
    <div className="result">
      <div className="result-header">
        <div>
          <h3>{result.sku}</h3>
          <p className="result-description">{result.description}</p>
        </div>
        <div className="result-score">{pct}%</div>
      </div>

      <div className="score-bar">
        <div className="score-fill" style={{ width: `${Math.max(8, pct)}%` }} />
      </div>

      <div className="chips">
        {result.evidence.map((e, i) => (
          <span key={`${result.sku}-${i}`} className="chip">{e}</span>
        ))}
      </div>

      <div className="actions">
        {!saving ? (
          <>
            <button className="primary" onClick={onApprove}>Approve</button>
            <button className="danger" onClick={onReject}>Reject</button>
          </>
        ) : (
          <span className="saved-state">Saved</span>
        )}
      </div>

      {route === "review" && <div className="review-note">Review required before accepting this match.</div>}
    </div>
  );
}
