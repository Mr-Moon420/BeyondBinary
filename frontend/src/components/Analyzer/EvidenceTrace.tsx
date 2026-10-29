import type { VerifiedClaim } from '../../types/api';

export function EvidenceTrace({ claim }: { claim: VerifiedClaim }) {
  if (!claim.evidence_trace) return null;
  const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
  return (
    <details className="mb-4 rounded border border-stone-200 bg-stone-50 p-3 text-xs">
      <summary className="cursor-pointer font-semibold text-stone-900">Evidence probabilities & verdict trace</summary>
      <p className="mt-3 mb-2">{claim.decision?.reason}</p>
      <p className="mb-3 text-stone-500">{claim.decision?.evaluated_count} passages evaluated; {claim.decision?.eligible_count} eligible. NLI probabilities are model scores, not calibrated factual accuracy.</p>
      {claim.evidence_trace.length === 0 && <p>No usable evidence was retrieved.</p>}
      {claim.evidence_trace.map(row => (
        <div key={row.id} className="border-t border-stone-200 py-3 space-y-2">
          <div className="font-semibold">{row.id} · {row.source.url ? <a className="underline" href={row.source.url} target="_blank" rel="noopener noreferrer">{row.source.title || row.source.url}</a> : row.source.title}</div>
          <blockquote className="border-l-2 border-stone-300 pl-2">{row.sentence}</blockquote>
          {row.probabilities ? <div className="flex flex-wrap gap-3 font-mono-data">
            <span>Entailment {pct(row.probabilities.entailment)}</span>
            <span>Contradiction {pct(row.probabilities.contradiction)}</span>
            <span>Neutral {pct(row.probabilities.neutral)}</span>
          </div> : <p>NLI probabilities unavailable.</p>}
          <p><strong>{row.eligible ? 'Eligible for aggregation' : 'Excluded from verdict'}:</strong> {row.eligibility_reason}</p>
          <p>Removing {row.id}: <strong>{row.without_verdict}</strong>{row.verdict_changes_without ? ' (verdict changes)' : ' (verdict unchanged)'}. Support-margin change: {(row.support_margin_change * 100).toFixed(1)} percentage points.</p>
          {claim.decision?.most_influential_evidence === row.id && <p className="font-semibold">Largest measured influence in this retrieval set; ties are possible.</p>}
        </div>
      ))}
      <p className="mt-2 text-stone-500">{claim.decision?.method}</p>
      <p className="mt-2 text-stone-500">Support margin is the mean of entailment minus contradiction over eligible passages. Its change can be large even when the final verdict stays the same.</p>
    </details>
  );
}
