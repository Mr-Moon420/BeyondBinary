import type { FC } from 'react';
import { Layers, ExternalLink, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';
import type { CrossSourceDistribution } from '../../types/api';
import { getBiasBadgeColor } from '../../utils/helpers';

interface EchoChamberMatrixProps {
  crossSource: CrossSourceDistribution | null;
}

export const EchoChamberMatrix: FC<EchoChamberMatrixProps> = ({ crossSource }) => {
  if (!crossSource || crossSource.total_sources === 0) {
    return null;
  }

  const { distribution, total_sources, total_rated, sources } = crossSource;

  const segments = [
    { label: 'Left', count: distribution['Left'] || 0, color: 'bg-blue-800' },
    { label: 'Lean Left', count: distribution['Lean Left'] || 0, color: 'bg-sky-600' },
    { label: 'Center', count: distribution['Center'] || 0, color: 'bg-stone-500' },
    { label: 'Lean Right', count: distribution['Lean Right'] || 0, color: 'bg-amber-600' },
    { label: 'Right', count: distribution['Right'] || 0, color: 'bg-rose-800' },
    { label: 'Unrated', count: distribution['Unrated'] || 0, color: 'bg-zinc-400' },
  ];

  const leftTotal = (distribution['Left'] || 0) + (distribution['Lean Left'] || 0);
  const rightTotal = (distribution['Right'] || 0) + (distribution['Lean Right'] || 0);

  let balanceStatus: { label: string; desc: string; icon: any; style: string } = {
    label: 'Balanced Verification Scope',
    desc: 'Retrieved evidence spans an ideologically diverse spread of reporting.',
    icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />,
    style: 'bg-emerald-50 text-emerald-900 border-emerald-200',
  };

  if (total_rated > 0) {
    const leftPct = leftTotal / total_rated;
    const rightPct = rightTotal / total_rated;
    const imbalance = Math.abs(leftPct - rightPct);

    if (imbalance >= 0.5) {
      const dir = leftPct > rightPct ? 'Left' : 'Right';
      balanceStatus = {
        label: `Corroboration Asymmetry (${dir} Skew)`,
        desc: `Verifying evidence disproportionately originates from ${dir}-leaning outlets.`,
        icon: <AlertCircle className="w-3.5 h-3.5 text-rose-700" />,
        style: 'bg-rose-50 text-rose-900 border-rose-200',
      };
    } else if (imbalance >= 0.25) {
      const dir = leftPct > rightPct ? 'Left' : 'Right';
      balanceStatus = {
        label: `Mild ${dir} Lean in Evidence`,
        desc: `A modest tilt towards ${dir}-leaning reporting was observed in search results.`,
        icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />,
        style: 'bg-amber-50 text-amber-900 border-amber-200',
      };
    }
  }

  const seen = new Set<string>();
  const uniqueSources = sources.filter((s) => {
    const k = s.domain || s.url;
    if (!k || seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  return (
    <div className="editorial-card rounded-md p-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-stone-700" />
          <span className="text-xs font-mono-data uppercase font-bold tracking-wider text-stone-900">
            Cross-Source Evidence Footprint
          </span>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono-data font-semibold border ${balanceStatus.style}`}
        >
          {balanceStatus.icon}
          <span>{balanceStatus.label}</span>
        </span>
      </div>

      <p className="text-xs text-stone-600 mb-4 leading-relaxed font-sans">
        {balanceStatus.desc}
      </p>

      {/* Ribbon */}
      <div className="h-3 w-full rounded bg-stone-100 overflow-hidden flex mb-3 border border-stone-200">
        {segments.map((seg) => {
          if (seg.count === 0) return null;
          const widthPct = (seg.count / total_sources) * 100;
          return (
            <div
              key={seg.label}
              style={{ width: `${widthPct}%` }}
              className={`${seg.color} h-full`}
              title={`${seg.label}: ${seg.count} sources (${Math.round(widthPct)}%)`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono-data mb-4">
        {segments.map((seg) => {
          if (seg.count === 0) return null;
          return (
            <div key={seg.label} className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${seg.color}`} />
              <span className="text-stone-600">
                {seg.label}: <strong className="text-stone-900">{seg.count}</strong>
              </span>
            </div>
          );
        })}
      </div>

      {/* Outlet badges */}
      <div className="pt-3 border-t border-stone-100">
        <div className="text-[10px] uppercase font-mono-data font-bold text-stone-400 tracking-wider mb-2">
          Consulted Media Sources ({uniqueSources.length})
        </div>

        <div className="flex flex-wrap gap-1.5">
          {uniqueSources.map((src, i) => {
            const colors = getBiasBadgeColor(src.bias);
            return (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono-data border ${colors.bg} ${colors.border} ${colors.text} hover:opacity-80 transition-opacity`}
              >
                <span>{src.outlet || src.domain}</span>
                <span className="text-[9px] opacity-70">[{src.bias || 'Unrated'}]</span>
                <ExternalLink className="w-2.5 h-2.5 opacity-50" />
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
};
