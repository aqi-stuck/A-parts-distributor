import { useMemo, useState } from "react";
import { search, feedback } from "../api";
import type { SearchResponse, SearchResult } from "../api";

type EvidenceChip = {
  label: string;
  value: string | null;
};

function humanizeEvidenceLabel(label: string): string {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function parseEvidence(evidence: string): EvidenceChip[] {
  const separator = evidence.indexOf(":");
  if (separator < 0) return [{ label: evidence, value: null }];

  const rawLabel = evidence.slice(0, separator).trim();
  const rawValue = evidence.slice(separator + 1).trim();
  if (rawLabel === "attributes") {
    const body = rawValue.match(/^\{([\s\S]*)\}$/)?.[1];
    if (body) {
      const attributes = Array.from(
        body.matchAll(/(['"])(.*?)\1\s*:\s*(['"])(.*?)\3/g),
        (match) => ({
          label: humanizeEvidenceLabel(match[2]),
          value: match[4],
        }),
      );
      if (attributes.length > 0) return attributes;
    }
  }

  const value = rawValue.replace(/^(['"])(.*)\1$/, "$2");
  return [{ label: humanizeEvidenceLabel(rawLabel), value }];
}

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
              <h3>{data.route === "auto" ? "Auto answer" : "Needs review"}</h3>
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
}: {
  result: SearchResult;
  route: "auto" | "review";
  saving: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const pct = Math.min(100, Math.max(0, Math.round(result.score * 100)));
  return (
    <article className="result">
      <div className="result-header">
        <div>
          <h3>{result.sku}</h3>
          <p className="result-description">{result.description}</p>
        </div>
        <div className="result-score">{pct}%</div>
      </div>

      <div
        className="score-bar"
        role="progressbar"
        aria-label={`Match score for ${result.sku}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="score-fill" style={{ width: `${100 - Math.max(8, pct)}%` }} />
      </div>

      <div className="chips" aria-label={`Match evidence for ${result.sku}`}>
        {result.evidence.flatMap((evidence, evidenceIndex) =>
          parseEvidence(evidence).map((chip, chipIndex) => (
            <span className="chip" key={`${result.sku}-${evidenceIndex}-${chipIndex}`}>
              <span className="chip-label">{chip.label}</span>
              {chip.value !== null && <span className="chip-value">{chip.value}</span>}
            </span>
          )),
        )}
      </div>
    </article>
  );
}
