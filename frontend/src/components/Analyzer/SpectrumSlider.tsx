import type { FC } from 'react';
import { Compass, BookOpen, BrainCircuit } from 'lucide-react';
import type { BiasAnalysis } from '../../types/api';
import { getBiasBadgeColor } from '../../utils/helpers';

interface SpectrumSliderProps {
  bias: BiasAnalysis;
}

export const SpectrumSlider: FC<SpectrumSliderProps> = ({ bias }) => {
  const score = bias.spectrum_score ?? 0;
  // Normalize -1.0 to +1.0 -> 3% to 97%
  const pinPercent = Math.max(3, Math.min(97, ((score + 1.0) / 2.0) * 100));
  const biasColors = getBiasBadgeColor(bias.bias_label);

  return (
    <div className="editorial-card rounded-md p-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-4">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-stone-700" />
          <span className="text-xs font-mono-data uppercase font-bold tracking-wider text-stone-900">
            Ideological Stance & Leaning
          </span>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono-data font-semibold border ${biasColors.bg} ${biasColors.text} ${biasColors.border}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${biasColors.dot}`} />
          <span>
            {bias.bias_label} ({score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)})
          </span>
        </span>
      </div>

      {/* Continuum Track */}
      <div className="relative py-4 mb-2">
        {/* Track bar */}
        <div className="h-2 w-full rounded-full bg-stone-200 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-stone-300 to-rose-700 opacity-80" />
        </div>

        {/* Center line marker */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-4 bg-stone-800 pointer-events-none" />

        {/* Needle Pin */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex flex-col items-center z-10 transition-all duration-500 ease-out"
          style={{ left: `${pinPercent}%` }}
        >
          <div className="w-4 h-4 rounded-full bg-stone-900 border-2 border-white shadow-sm flex items-center justify-center" />
        </div>

        {/* Ticks */}
        <div className="flex justify-between text-[10px] font-mono-data text-stone-500 uppercase mt-2">
          <span>Far Left (-1.0)</span>
          <span>Center (0.0)</span>
          <span>Far Right (+1.0)</span>
        </div>
      </div>

      {/* Dual Calibration Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-stone-100 mt-3 text-xs">
        <div className="p-3 bg-stone-50 rounded border border-stone-200/80">
          <div className="flex items-center gap-1 text-stone-500 text-[11px] font-mono-data uppercase mb-1">
            <BookOpen className="w-3 h-3 text-stone-400" />
            <span>AllSides Domain Prior (60%)</span>
          </div>
          <div className="font-semibold text-stone-900">
            {bias.domain_rating ? (
              <span>
                {bias.domain_rating.name}{' '}
                <span className="text-stone-500 font-mono-data font-normal">
                  [{bias.domain_rating.bias}]
                </span>
              </span>
            ) : (
              <span className="text-stone-400 font-normal italic">
                Domain unrated in database
              </span>
            )}
          </div>
        </div>

        <div className="p-3 bg-stone-50 rounded border border-stone-200/80">
          <div className="flex items-center gap-1 text-stone-500 text-[11px] font-mono-data uppercase mb-1">
            <BrainCircuit className="w-3 h-3 text-stone-400" />
            <span>BERT Text Model (40%)</span>
          </div>
          <div className="font-mono-data text-xs text-stone-800 flex items-center gap-2 font-semibold">
            <span className="text-blue-900">
              L: {Math.round((bias.stance?.probabilities?.left ?? 0) * 100)}%
            </span>
            <span className="text-stone-300">/</span>
            <span className="text-stone-700">
              C: {Math.round((bias.stance?.probabilities?.center ?? 0) * 100)}%
            </span>
            <span className="text-stone-300">/</span>
            <span className="text-rose-900">
              R: {Math.round((bias.stance?.probabilities?.right ?? 0) * 100)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
