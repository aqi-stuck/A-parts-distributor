import { useMemo, useState } from "react";
import { search, feedback } from "../api";
import type { SearchResponse, SearchResult } from "../api";
import { ResultCard } from "../components/ResultCard";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canRetrySearch, setCanRetrySearch] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const doSearch = async () => {
    const q = query.trim();
    if (!q) {
      setCanRetrySearch(false);
      setData(null);
      setError("Enter a part description before searching.");
      return;
    }

    setLoading(true);
    setError(null);
    setCanRetrySearch(false);
    setNotice(null);
    setData(null);
    setLastQuery(q);

    try {
      const res = await search(q);
      setData(res);
    } catch {
      setError("Could not reach the search service. Please try again.");
      setCanRetrySearch(true);
    } finally {
      setLoading(false);
    }
  };

  const onApproveReject = async (sku: string, decision: "approve" | "reject") => {
    try {
      setSavingId(sku);
      setError(null);
      setCanRetrySearch(false);
      setNotice(null);
      await feedback(lastQuery || query, sku, decision);
      setNotice(`${decision === "approve" ? "Approved" : "Rejected"} ${sku}.`);
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

      {loading && <div className="status-box">Searching catalog...</div>}
      {error && (
        <div className="banner error">
          {error}
          {canRetrySearch && (
            <button onClick={doSearch} className="secondary-button" disabled={loading}>
              Retry
            </button>
          )}
        </div>
      )}
      {notice && <p className="saved-state" role="status">{notice}</p>}

      {data && (
        <>
          {summary && (
            <div className={`summary-card ${data.route}`}>
              <h3>{data.route === "auto" ? "Confident Match" : "Needs review"}</h3>
            </div>
          )}

          {data.results.length === 0 ? (
            <p className="empty-state">No matching parts found. This request should be sent to a human reviewer.</p>
          ) : (
            data.results.map((r: SearchResult, index) => (
              <ResultCard
                key={r.sku}
                result={r}
                isTopResult={index === 0}
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
