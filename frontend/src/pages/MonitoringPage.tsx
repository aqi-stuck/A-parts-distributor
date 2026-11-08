import { useEffect, useState } from "react";
import { metrics } from "../api";
import type { Metrics } from "../api";

export function MonitoringPage() {
  const [data, setData] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    metrics().then(setData).catch(() => setError("Could not load metrics."));
  }, []);

  if (error) return <div className="card">{error}</div>;
  if (!data) return <div className="card">Loading...</div>;

  const rate = data.total_queries ? Math.round((data.review_count / data.total_queries) * 100) : 0;

  return (
    <section className="card">
      <h2>Monitoring</h2>
      <div className="grid">
        <div className="metric"><div>Total queries</div><div>{data.total_queries}</div></div>
        <div className="metric"><div>Sent to review</div><div>{data.review_count}</div></div>
        <div className="metric"><div>Average speed (ms)</div><div>{data.avg_latency_ms}</div></div>
        <div className="metric"><div>Review rate</div><div>{rate}%</div></div>
      </div>
      <p className="note">Review rate = Sent to review ÷ Total queries</p>
    </section>
  );
}
