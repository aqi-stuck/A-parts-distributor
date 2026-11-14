import type { SearchResult } from "../api";

type EvidencePanelProps = {
  result: SearchResult;
};

type EvidenceChip = {
  label: string;
  value: string | null;
  status: "matched" | "different" | "unspecified" | "neutral";
};

function humanizeLabel(label: string): string {
  const knownLabels: Record<string, string> = {
    category: "Part type",
    length_mm: "Length",
    thread: "Thread size",
  };
  if (knownLabels[label]) return knownLabels[label];

  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function parseEvidence(evidence: string): EvidenceChip[] {
  const separator = evidence.indexOf(":");
  if (separator < 0) return [{ label: evidence, value: null, status: "neutral" }];

  const label = evidence.slice(0, separator).trim();
  const rawValue = evidence.slice(separator + 1).trim();
  if (["normalized_query", "attributes", "attribute_agreement", "score_margin"].includes(label)) {
    return [];
  }

  if (
    label === "matched attribute" ||
    label === "different attribute" ||
    label === "missing attribute"
  ) {
    const [field, ...valueParts] = rawValue.split("=");
    return [{
      label: humanizeLabel(field.trim()),
      value: valueParts.join("=").trim(),
      status: label === "matched attribute" ? "matched" : "different",
    }];
  }
  if (label === "not specified") {
    return [{ label: humanizeLabel(rawValue), value: null, status: "unspecified" }];
  }

  const value = rawValue.replace(/^(['"])(.*)\1$/, "$2");
  return [{ label: humanizeLabel(label), value, status: "neutral" }];
}

export function EvidencePanel({ result }: EvidencePanelProps) {
  const chips = result.evidence.flatMap(parseEvidence);

  return (
    <section className="evidence-panel" aria-label={`Evidence for ${result.sku}`}>
      {chips.length > 0 ? (
        <div className="chips">
          {chips.map((chip, index) => (
            <span className={`chip ${chip.status}`} key={index}>
              {chip.status !== "neutral" && (
                <span className="chip-label">
                  {chip.status === "matched"
                    ? "Present"
                    : chip.status === "different"
                      ? "Different"
                      : "Not specified"}
                  :
                </span>
              )}
              <span className="chip-label">{chip.label}</span>
              {chip.value !== null && <span className="chip-value">{chip.value}</span>}
            </span>
          ))}
        </div>
      ) : (
        <p className="evidence-empty">No specific attributes found.</p>
      )}
    </section>
  );
}
