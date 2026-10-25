import type { FC } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, FileCheck } from 'lucide-react';
import type { VerifiedClaim } from '../../types/api';

interface CredibilityGaugeProps {
  score: number;
  claims: VerifiedClaim[];
}

export const CredibilityGauge: FC<CredibilityGaugeProps> = ({ score, claims }) => {
  const isHigh = score >= 70;
  const isMedium = score >= 40 && score < 70;

  const verdictLabel = isHigh
    ? 'High Factual Integrity'
    : isMedium
    ? 'Mixed / Contested Reporting'
    : 'Significant Factual Deficiencies';

  const verdictBadgeStyle = isHigh
    ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
    : isMedium
    ? 'bg-amber-50 text-amber-900 border-amber-200'
    : 'bg-rose-50 text-rose-900 border-rose-200';

  const verdictIcon = isHigh ? (
    <ShieldCheck className="w-4 h-4 text-emerald-700" />
  ) : isMedium ? (
    <AlertTriangle className="w-4 h-4 text-amber-700" />
  ) : (
    <ShieldAlert className="w-4 h-4 text-rose-700" />
  );

  const supported = claims.filter((c) => c.verdict === 'Supported').length;
  const refuted = claims.filter((c) => c.verdict === 'Refuted').length;
  const framing = claims.filter((c) => c.verdict === 'Misleading-Framing').length;
  const neutral = claims.filter((c) => c.verdict === 'Not Enough Info').length;

  return (
    <div className="editorial-card rounded-md p-6">
      {/* Dossier Header */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-4">
        <div className="flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-stone-700" />
          <span className="text-xs font-mono-data uppercase font-bold tracking-wider text-stone-900">
            Factual Accuracy Assessment
          </span>
        </div>
        <span className="text-[11px] font-mono-data text-stone-400">
          Metric Bounds: 0–100
        </span>
      </div>

      {/* Primary Score Metric */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 mb-5">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl sm:text-6xl font-editorial font-bold text-stone-900 tracking-tight">
              {score.toFixed(1)}
            </span>
            <span className="text-xl font-editorial text-stone-400 font-normal">
              / 100
            </span>
          </div>
          <p className="text-xs text-stone-500 font-mono-data mt-1">
            Confidence-weighted premise inference score
          </p>
        </div>

        <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded border text-xs font-semibold ${verdictBadgeStyle}`}>
          {verdictIcon}
          <span>{verdictLabel}</span>
        </div>
      </div>

      {/* Progress Bar (Crisp flat editorial rule) */}
      <div className="w-full bg-stone-100 h-2 rounded-full overflow-hidden mb-5">
        <div
          className={`h-full transition-all duration-700 ${
            isHigh ? 'bg-emerald-700' : isMedium ? 'bg-amber-600' : 'bg-rose-700'
          }`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>

      {/* Ledger Table */}
      <div className="grid grid-cols-4 gap-2 pt-3 border-t border-stone-100 text-center font-mono-data">
        <div className="p-2 bg-stone-50 rounded border border-stone-100">
          <div className="text-lg font-bold text-emerald-800">{supported}</div>
          <div className="text-[10px] text-stone-500 uppercase font-semibold">Entailed</div>
        </div>

        <div className="p-2 bg-stone-50 rounded border border-stone-100">
          <div className="text-lg font-bold text-rose-800">{refuted}</div>
          <div className="text-[10px] text-stone-500 uppercase font-semibold">Refuted</div>
        </div>

        <div className="p-2 bg-stone-50 rounded border border-stone-100">
          <div className="text-lg font-bold text-amber-800">{framing}</div>
          <div className="text-[10px] text-stone-500 uppercase font-semibold">Framing</div>
        </div>

        <div className="p-2 bg-stone-50 rounded border border-stone-100">
          <div className="text-lg font-bold text-stone-700">{neutral}</div>
          <div className="text-[10px] text-stone-500 uppercase font-semibold">Unverified</div>
        </div>
      </div>
    </div>
  );
};
