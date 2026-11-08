import { useState } from "react";
import { search, feedback } from "../api";
import type { SearchResponse, SearchResult } from "../api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const doSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await search(q);
      setData(res);
    } catch {
      setError("Could not reach the search service. Please try again.");
    }
    setLoading(false);
  };

  const onApproveReject = async (sku: string, decision: "approve" | "reject") => {
    try {
      setSavingId(sku);
      await feedback(query, sku, decision);
    } catch {
      // show fail
    } finally {
      setSavingId(null);
    }
  };

  return (
    <section className="card">
      <h2>Search parts</h2>
      <label>Part description</label>
      <div className="input-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a part description, e.g. hex bolt 1/2 zinc"
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
        />
        <button onClick={doSearch}>Search</button>
      </div>
      <p className="helper">Press Enter to search</p>

      {loading && <div>Searching catalog...</div>}
      {error && (
        <div className="banner error">
          {error}
          <button onClick={doSearch}>Retry</button>
        </div>
      )}

      {data && (
        <>
          <div>
            <span className={`badge ${data.route}`}>
              {data.route === "auto" ? "Auto answer" : "Needs review"}
            </span>
            {data.route === "review" && data.reason && <div>{data.reason}</div>}
          </div>

          {data.results.length === 0 ? (
            <p>No matching parts found. Send to a human reviewer.</p>
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
          <div className="footer">Answered in {data.latency_ms} ms</div>
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
      <h3>{result.sku}</h3>
      <p>{result.description}</p>
      <div>Score {pct}%</div>
      <div className="score-bar"><div className="score-fill" style={{ width: `${pct}%` }} /></div>
      <div className="chips">
        {result.evidence.map((e, i) => (
          <span key={i} className="chip">{e}</span>
        ))}
      </div>
      <div className="actions">
        {!saving ? (
          <>
            <button className="primary" onClick={onApprove}>Approve</button>
            <button className="danger" onClick={onReject}>Reject</button>
          </>
        ) : (
          <span>Saved</span>
        )}
      </div>
      {route === "review" && <div>Unconfirmed</div>}
    </div>
  );
}
