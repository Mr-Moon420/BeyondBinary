import type { FC } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  Search,
  Lightbulb,
} from 'lucide-react';
import type { VerifiedClaim } from '../../types/api';
import { getVerdictBadgeColor } from '../../utils/helpers';

interface ClaimsListProps {
  claims: VerifiedClaim[];
}

export const ClaimsList: FC<ClaimsListProps> = ({ claims }) => {
  if (!claims || claims.length === 0) {
    return (
      <div className="editorial-card rounded-md p-8 text-center text-stone-500 font-sans text-xs">
        No check-worthy factual assertions extracted from this material.
      </div>
    );
  }

  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case 'Supported':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />;
      case 'Refuted':
        return <XCircle className="w-3.5 h-3.5 text-rose-700" />;
      case 'Misleading-Framing':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />;
      default:
        return <HelpCircle className="w-3.5 h-3.5 text-zinc-600" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-stone-700" />
          <h3 className="text-xs font-mono-data font-bold uppercase tracking-wider text-stone-900">
            Itemized Fact-Checking Verification Ledger ({claims.length} Claims)
          </h3>
        </div>
        <span className="text-[11px] font-mono-data text-stone-500">
          DeBERTa CFS Filter + RoBERTa Large NLI
        </span>
      </div>

      <div className="space-y-4">
        {claims.map((claim, idx) => {
          const colors = getVerdictBadgeColor(claim.verdict);
          const confPct = Math.round((claim.confidence ?? 1) * 100);

          const evidenceSnippet = Array.isArray(claim.evidence)
            ? claim.evidence[0]
            : claim.evidence || 'No direct corroborating evidence retrieved.';

          return (
            <div
              key={idx}
              className="editorial-card rounded-md p-5 sm:p-6 transition-all border-l-4 border-l-stone-900"
            >
              {/* Header row: Claim index & Verdict Stamp */}
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono-data font-bold text-stone-500 uppercase">
                    Claim #{idx + 1}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono-data font-bold border ${colors.badge}`}
                  >
                    {getVerdictIcon(claim.verdict)}
                    <span>{claim.verdict.toUpperCase()}</span>
                  </span>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono-data text-stone-500">
                  <span>Confidence: <strong className="text-stone-900">{confPct}%</strong></span>
                  {claim.retrieval_source && (
                    <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200">
                      <Search className="w-3 h-3 text-stone-400" />
                      <span>{claim.retrieval_source}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Claim Statement */}
              <blockquote className="font-editorial text-base sm:text-lg font-semibold text-stone-900 leading-snug mb-3.5 pl-3 border-l-2 border-stone-300 italic">
                "{claim.claim}"
              </blockquote>

              {/* XAI Neural Explainability Rationale */}
              {claim.xai_rationale && (
                <div className="mb-3.5 p-3.5 rounded bg-stone-900 text-white text-xs border border-stone-800 shadow-xs">
                  <div className="flex items-center justify-between gap-2 pb-2 border-b border-stone-700/80 mb-2">
                    <div className="flex items-center gap-1.5 text-amber-400">
                      <Lightbulb className="w-3.5 h-3.5 fill-current" />
                      <span className="text-[10px] font-mono-data font-bold uppercase tracking-wider">
                        XAI Diagnostic Rationale
                      </span>
                    </div>
                    <span className="text-[10px] font-mono-data font-semibold px-2 py-0.5 rounded bg-stone-800 text-stone-300 border border-stone-700">
                      {claim.xai_rationale.category}
                    </span>
                  </div>

                  <p className="text-xs font-sans text-stone-200 leading-relaxed italic mb-2">
                    "{claim.xai_rationale.rationale}"
                  </p>

                  {/* Conflict Diff (if any) */}
                  {claim.xai_rationale.conflict_diff && claim.xai_rationale.conflict_diff.length > 0 && (
                    <div className="pt-2 border-t border-stone-800 flex flex-wrap gap-2 items-center">
                      <span className="text-[10px] font-mono-data text-stone-400 uppercase tracking-wider font-semibold">
                        Semantic Conflict Diff:
                      </span>
                      {claim.xai_rationale.conflict_diff.map((diff, dIdx) => (
                        <span key={dIdx} className="inline-flex items-center gap-1 text-[11px] font-mono-data bg-stone-800 px-2 py-0.5 rounded border border-stone-700">
                          <span className="text-stone-400">{diff.type}:</span>
                          <span className="text-rose-400 line-through font-semibold">{diff.claim_val}</span>
                          <span className="text-stone-500">≠</span>
                          <span className="text-emerald-400 font-bold">{diff.evidence_val}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Corroborating Anchors (for supported) */}
                  {claim.xai_rationale.alignment_entities && claim.xai_rationale.alignment_entities.length > 0 && (
                    <div className="pt-2 border-t border-stone-800 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] font-mono-data text-stone-400 uppercase tracking-wider font-semibold mr-1">
                        Verified Anchors:
                      </span>
                      {claim.xai_rationale.alignment_entities.map((ent, eIdx) => (
                        <span key={eIdx} className="text-[10px] font-mono-data bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-medium">
                          ✓ {ent}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Misleading Framing Banner */}
              {claim.framing_analysis?.is_misleading && (
                <div className="mb-3.5 p-3 rounded bg-amber-50 border border-amber-200 text-amber-950 text-xs flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-0.5">
                      Rhetorical Framing Alert:
                    </strong>
                    <span>{claim.framing_analysis.explanation}</span>
                  </div>
                </div>
              )}

              {/* Corroborating Evidence */}
              <div className="bg-[#FAF9F5] p-3.5 rounded border border-stone-200 text-xs">
                <div className="text-[10px] uppercase font-mono-data font-bold text-stone-400 tracking-wider mb-1">
                  Retrieved External Corroborating Evidence
                </div>
                <p className="text-stone-800 leading-relaxed font-sans">
                  "{evidenceSnippet}"
                </p>

                {/* Citations */}
                {claim.sources && claim.sources.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-stone-200/80 flex flex-wrap gap-2 items-center">
                    <span className="text-[10px] font-mono-data font-semibold text-stone-400 uppercase">
                      Primary Sources:
                    </span>
                    {claim.sources
                      .filter((s) => s.url)
                      .slice(0, 3)
                      .map((src, sIdx) => (
                        <a
                          key={sIdx}
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-stone-800 hover:text-stone-950 font-mono-data underline underline-offset-2"
                        >
                          <span>{src.title ? src.title.slice(0, 35) + '...' : 'Evidence Citation'}</span>
                          <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                        </a>
                      ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
