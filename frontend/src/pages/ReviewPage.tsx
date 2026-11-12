import { useEffect, useState } from "react";
import { feedback, reviewQueue } from "../api";
import type { ReviewItem } from "../api";

export function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  useEffect(() => {
    reviewQueue()
      .then(setItems)
      .catch(() => setError("Could not load review queue."));
  }, []);

  const submitDecision = async (
    item: ReviewItem,
    decision: "approve" | "correct" | "reject",
    sku: string | null,
  ) => {
    setSavingId(item.id);
    setError(null);
    setNotice(null);
    try {
      await feedback(item.query, sku, decision, item.id);
      setItems((current) => current?.filter((entry) => entry.id !== item.id) ?? []);
      setNotice(`Review saved for “${item.query}”.`);
    } catch {
      setError("Could not save this review decision. The item is still in the queue.");
    } finally {
      setSavingId(null);
    }
  };

  if (items === null && !error) return <section className="card">Loading review queue...</section>;

  return (
    <div className="review-page">
      {error && <div className="banner error" role="alert">{error}</div>}
      {notice && <p className="saved-state" role="status">{notice}</p>}
      {items?.length === 0 && <p className="empty-state">Nothing to review right now.</p>}
      {items?.map((item) => {
        const saving = savingId === item.id;
        return (
          <article
            className="w-full rounded-md border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
            key={item.id}
          >
            <header className="flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Review request</p>
                <h2 className="mt-1 break-words text-base font-semibold text-slate-900">
                  “{item.query}”
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {new Date(item.created_at).toLocaleString()} <span aria-hidden="true">·</span> {item.latency_ms} ms
                </p>
              </div>
              <div className="shrink-0 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <span className="font-medium">Top match:</span> {item.top_sku ?? "No match"}
              </div>
            </header>

            <div className="pt-4">
              <h3 className="text-sm font-semibold text-slate-700">Suggested parts</h3>
              {item.results.length > 0 ? (
                <div className="mt-2 grid gap-2">
                  {item.results.map((candidate) => (
                    <button
                      className="!flex !h-auto !w-full !items-center !justify-between !gap-4 !rounded-md !border !border-slate-200 !bg-slate-50 !px-3 !py-3 !text-left !text-slate-800 transition hover:!border-blue-300 hover:!bg-blue-50 disabled:!cursor-wait disabled:!opacity-60"
                      key={candidate.sku}
                      disabled={saving}
                      onClick={() => submitDecision(item, "approve", candidate.sku)}
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-slate-900">{candidate.sku}</span>
                        <span className="mt-0.5 block text-sm font-normal text-slate-600">{candidate.description}</span>
                      </span>
                      <span className="shrink-0 text-sm font-semibold text-blue-700">
                        {Math.round(candidate.score * 100)}%
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">The search returned no candidate parts.</p>
              )}
            </div>

            <footer className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
              <button
                className="!h-auto !rounded-lg !border !border-red-200 !bg-white !px-3 !py-2 !text-sm !text-red-700 transition hover:!bg-red-50 disabled:!cursor-wait disabled:!opacity-60"
                disabled={saving}
                onClick={() => submitDecision(item, "reject", null)}
              >
                Reject all suggestions
              </button>
              {saving && <span className="text-sm text-slate-500">Saving decision...</span>}
            </footer>
          </article>
        );
      })}
    </div>
  );
}
