import { useEffect, useState } from "react";
import { metrics } from "../api";
import type { Metrics } from "../api";

export function MonitoringPage() {
  const [data, setData] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await metrics());
    } catch {
      setError("Could not load monitoring metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    metrics()
      .then((response) => {
        if (active) setData(response);
      })
      .catch(() => {
        if (active) setError("Could not load monitoring metrics.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const escalationRate =
    data && data.total_queries > 0
      ? `${((data.review_count / data.total_queries) * 100).toFixed(1)}%`
      : "—";
  const hasDriftScore =
    data !== null &&
    typeof data.drift_score === "number" &&
    Number.isFinite(data.drift_score);
  const driftAlert =
    data?.drift_alert === true
      ? "Alert detected"
      : data?.drift_alert === false
        ? "No alert"
        : "Alert state unavailable";
  const driftStatusClass =
    data?.drift_alert === true
      ? "alert"
      : data?.drift_alert === false
        ? "normal"
        : "unavailable";

  const retryButton = (
    <button
      type="button"
      className="secondary-button"
      onClick={() => void loadMetrics()}
      disabled={loading}
    >
      {loading ? "Refreshing..." : "Retry"}
    </button>
  );

  return (
    <section className="card monitoring-page">
      <header className="monitoring-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Monitoring</h2>
          <p className="monitoring-description">
            Search volume, escalations, latency, and drift status.
          </p>
        </div>
        {data && (
          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadMetrics()}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        )}
      </header>

      {error && (
        <div className="banner error" role="alert">
          <span>{error}</span>
          {!data && retryButton}
        </div>
      )}

      {data ? (
        <>
          <div className="monitoring-grid">
            <article className="monitoring-metric">
              <p className="monitoring-metric-label">Total queries</p>
              <p className="monitoring-metric-value">{data.total_queries}</p>
              <p className="monitoring-metric-detail">Queries recorded</p>
            </article>
            <article className="monitoring-metric">
              <p className="monitoring-metric-label">Escalation rate</p>
              <p className="monitoring-metric-value">{escalationRate}</p>
              <p className="monitoring-metric-detail">
                {data.review_count} of {data.total_queries} sent to review
              </p>
            </article>
            <article className="monitoring-metric">
              <p className="monitoring-metric-label">Average latency</p>
              <p className="monitoring-metric-value">
                {data.avg_latency_ms.toFixed(1)} ms
              </p>
              <p className="monitoring-metric-detail">Across recorded queries</p>
            </article>
            <article className="monitoring-metric">
              <p className="monitoring-metric-label">Drift score</p>
              <p className="monitoring-metric-value">
                {hasDriftScore ? data.drift_score?.toFixed(3) : "Unavailable"}
              </p>
              <p className={`monitoring-status ${driftStatusClass}`}>
                {driftAlert}
              </p>
            </article>
          </div>
          {(!hasDriftScore || typeof data.drift_alert !== "boolean") && (
            <p className="note">
              Drift score and alert state will appear when provided by the metrics API.
            </p>
          )}
        </>
      ) : loading ? (
        <div className="status-box" role="status">Loading monitoring metrics...</div>
      ) : (
        <p className="empty-state">Monitoring metrics are unavailable.</p>
      )}
    </section>
  );
}
