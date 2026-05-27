"use client";

import { useMemo, useState } from "react";

export type ProfileFactPolicy = {
  capture_terms: Record<string, string[]>;
  blocked_terms: Record<string, string[]>;
  ttl_days_by_type: Record<string, number>;
};

const factTypes = [
  "name",
  "relationship",
  "workplace",
  "location",
  "date",
  "belief",
  "health_context",
  "habit",
  "timezone"
];

const ttlOptions = [
  { label: "30 days", value: 30 },
  { label: "3 months", value: 90 },
  { label: "6 months", value: 180 },
  { label: "12 months", value: 365 }
];

export function ProfilePolicyPanel({ initialPolicy }: { initialPolicy: ProfileFactPolicy }) {
  const [policy, setPolicy] = useState(initialPolicy);
  const [selectedType, setSelectedType] = useState(factTypes[0]);
  const [captureTerm, setCaptureTerm] = useState("");
  const [blockedTerm, setBlockedTerm] = useState("");
  const [globalBlockedTerm, setGlobalBlockedTerm] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const captureTerms = policy.capture_terms[selectedType] ?? [];
  const blockedTerms = policy.blocked_terms[selectedType] ?? [];
  const globalBlockedTerms = policy.blocked_terms.all ?? [];
  const preview = useMemo(
    () => factTypes.map((factType) => `${factType}: ${policy.ttl_days_by_type[factType] ?? 180}d`).join("  "),
    [policy.ttl_days_by_type]
  );

  function addTerm(group: "capture_terms" | "blocked_terms", factType: string, value: string) {
    const term = value.trim().toLowerCase();
    if (term.length < 2) return;
    setPolicy((current) => {
      const existing = current[group][factType] ?? [];
      if (existing.includes(term)) return current;
      return {
        ...current,
        [group]: {
          ...current[group],
          [factType]: [...existing, term]
        }
      };
    });
  }

  function removeTerm(group: "capture_terms" | "blocked_terms", factType: string, value: string) {
    setPolicy((current) => ({
      ...current,
      [group]: {
        ...current[group],
        [factType]: (current[group][factType] ?? []).filter((term) => term !== value)
      }
    }));
  }

  function setTtl(factType: string, ttl: number) {
    setPolicy((current) => ({
      ...current,
      ttl_days_by_type: {
        ...current.ttl_days_by_type,
        [factType]: ttl
      }
    }));
  }

  async function savePolicy() {
    setStatus("saving");
    try {
      const response = await fetch("/api/profile-facts/policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy)
      });
      if (!response.ok) throw new Error("save failed");
      setPolicy(await response.json());
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }

  return (
    <section id="profile-fact-policy" className="panel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">PII Capture Policy</p>
          <h3>Profile facts whitelist, blacklist, and expiry</h3>
        </div>
        <button type="button" onClick={savePolicy} disabled={status === "saving"}>
          {status === "saving" ? "Saving" : "Save policy"}
        </button>
      </div>

      <div className="policyGrid">
        <div className="policyColumn">
          <label htmlFor="fact-type">Fact type</label>
          <select id="fact-type" value={selectedType} onChange={(event) => setSelectedType(event.target.value)}>
            {factTypes.map((factType) => (
              <option key={factType} value={factType}>
                {factType.replace("_", " ")}
              </option>
            ))}
          </select>

          <label htmlFor="ttl">Expire after</label>
          <select
            id="ttl"
            value={policy.ttl_days_by_type[selectedType] ?? 180}
            onChange={(event) => setTtl(selectedType, Number(event.target.value))}
          >
            {ttlOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <TermEditor
          title="Whitelist"
          inputLabel={`Add ${selectedType.replace("_", " ")} capture term`}
          value={captureTerm}
          terms={captureTerms}
          onValueChange={setCaptureTerm}
          onAdd={() => {
            addTerm("capture_terms", selectedType, captureTerm);
            setCaptureTerm("");
          }}
          onRemove={(term) => removeTerm("capture_terms", selectedType, term)}
        />

        <TermEditor
          title="Blacklist"
          inputLabel={`Block ${selectedType.replace("_", " ")} term`}
          value={blockedTerm}
          terms={blockedTerms}
          onValueChange={setBlockedTerm}
          onAdd={() => {
            addTerm("blocked_terms", selectedType, blockedTerm);
            setBlockedTerm("");
          }}
          onRemove={(term) => removeTerm("blocked_terms", selectedType, term)}
        />
      </div>

      <div className="globalBlock">
        <p className="eyebrow">Global blacklist</p>
        <div className="chips">
          {globalBlockedTerms.map((term) => (
            <button key={term} type="button" onClick={() => removeTerm("blocked_terms", "all", term)}>
              {term} x
            </button>
          ))}
        </div>
        <div className="inlineForm">
          <input
            aria-label="Add global blacklist term"
            value={globalBlockedTerm}
            onChange={(event) => setGlobalBlockedTerm(event.target.value)}
            placeholder="Add global blocked term"
          />
          <button
            type="button"
            onClick={() => {
              addTerm("blocked_terms", "all", globalBlockedTerm);
              setGlobalBlockedTerm("");
            }}
          >
            Add
          </button>
        </div>
      </div>

      <p className="policyMeta">{preview}</p>
      {status === "saved" ? <p className="success">Policy saved.</p> : null}
      {status === "error" ? <p className="error">Policy could not be saved.</p> : null}
    </section>
  );
}

function TermEditor({
  title,
  inputLabel,
  value,
  terms,
  onValueChange,
  onAdd,
  onRemove
}: {
  title: string;
  inputLabel: string;
  value: string;
  terms: string[];
  onValueChange: (value: string) => void;
  onAdd: () => void;
  onRemove: (term: string) => void;
}) {
  return (
    <div className="policyColumn">
      <p className="fieldTitle">{title}</p>
      <div className="chips">
        {terms.map((term) => (
          <button key={term} type="button" onClick={() => onRemove(term)}>
            {term} x
          </button>
        ))}
      </div>
      <div className="inlineForm">
        <input aria-label={inputLabel} value={value} onChange={(event) => onValueChange(event.target.value)} placeholder={inputLabel} />
        <button type="button" onClick={onAdd}>
          Add
        </button>
      </div>
    </div>
  );
}
