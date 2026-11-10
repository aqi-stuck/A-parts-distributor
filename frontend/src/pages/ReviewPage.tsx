import { useEffect, useState } from "react";
import { reviewQueue } from "../api";
import type { ReviewItem } from "../api";

export function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth > 600);

  useEffect(() => {
    const onResize = () => setIsDesktop(window.innerWidth > 600);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      const data = await reviewQueue();
      setItems(data);
      setError(null);
    } catch {
      setError("Could not load review queue.");
    }
  };

  const openQuery = (q: string) => {
    window.location.hash = "#search";
    setTimeout(() => {
      // trigger search via hash change in SearchPage? We'll just set location and let user press search.
      // To automate, we could dispatch custom event but keep simple.
      const input = document.querySelector<HTMLInputElement>('input[placeholder*="Type a part"]');
      if (input) input.value = q;
    }, 0);
  };

  if (error) return <div className="card">{error}</div>;
  if (items === null) return <div className="card">Loading...</div>;
  if (items.length === 0) return <div className="card">Nothing to review right now.</div>;

  if (isDesktop) {
    return (
      <section className="card">
        <div className="page-header">
          <div>
            <p className="eyebrow">Human checks</p>
            <h2>Review queue</h2>
          </div>
        </div>
        <p className="helper">Queries that need a human to check.</p>
        <table>
          <thead>
            <tr><th>Query</th><th>Top suggested SKU</th><th>Latency ms</th><th>Time asked</th><th></th></tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td>{it.query}</td>
                <td>{it.top_sku ?? ""}</td>
                <td>{it.latency_ms}</td>
                <td>{new Date(it.created_at).toLocaleString()}</td>
                <td><button onClick={() => openQuery(it.query)}>Open query</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <p className="eyebrow">Human checks</p>
          <h2>Review queue</h2>
        </div>
      </div>
      <p className="helper">Queries that need a human to check.</p>
      {items.map((it, i) => (
        <div key={i} className="stack-card">
          <div><strong>{it.query}</strong></div>
          <div>Top SKU: {it.top_sku ?? ""}</div>
          <div>Latency: {it.latency_ms} ms</div>
          <div>{new Date(it.created_at).toLocaleString()}</div>
          <button onClick={() => openQuery(it.query)}>Open query</button>
        </div>
      ))}
    </section>
  );
}
