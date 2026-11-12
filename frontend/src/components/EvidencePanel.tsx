import type { SearchResult } from "../api";

type EvidencePanelProps = {
  result: SearchResult;
  route: "auto" | "review";
  reason?: string | null;
};

type EvidenceChip = {
  label: string;
  value: string | null;
};

function humanizeLabel(label: string): string {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function parseEvidence(evidence: string): EvidenceChip[] {
  const separator = evidence.indexOf(":");
  if (separator < 0) return [{ label: evidence, value: null }];

  const label = evidence.slice(0, separator).trim();
  const rawValue = evidence.slice(separator + 1).trim();
  if (label === "attributes") {
    const body = rawValue.match(/^\{([\s\S]*)\}$/)?.[1];
    if (body) {
      const attributes = Array.from(
        body.matchAll(/(['"])(.*?)\1\s*:\s*(['"])(.*?)\3/g),
        (match) => ({
          label: humanizeLabel(match[2]),
          value: match[4],
        }),
      );
      if (attributes.length > 0) return attributes;
    }
  }

  const value = rawValue.replace(/^(['"])(.*)\1$/, "$2");
  return [{ label: humanizeLabel(label), value }];
}

export function EvidencePanel({ result, route, reason }: EvidencePanelProps) {
  const confidence = Math.min(1, Math.max(0, result.confidence));
  const routeDescription =
    reason ?? (route === "auto" ? "No review required." : "Reason not provided.");

  return (
    <section className="evidence-panel" aria-label={`Evidence for ${result.sku}`}>
      <h4 className="evidence-title">Match evidence</h4>
      {result.evidence.length > 0 ? (
        <div className="chips">
          {result.evidence.flatMap((evidence, evidenceIndex) =>
            parseEvidence(evidence).map((chip, chipIndex) => (
              <span className="chip" key={`${evidenceIndex}-${chipIndex}`}>
                <span className="chip-label">{chip.label}</span>
                {chip.value !== null && <span className="chip-value">{chip.value}</span>}
              </span>
            )),
          )}
        </div>
      ) : (
        <p className="evidence-empty">No match evidence was provided.</p>
      )}
      <div className="evidence-context">
        <span className="confidence-badge">
          {confidence > 0
            ? `${Math.round(confidence * 100)}% confidence`
            : "Confidence unavailable"}
        </span>
        <p>
          <strong>Routing reason:</strong> {routeDescription}
        </p>
      </div>
    </section>
  );
}
