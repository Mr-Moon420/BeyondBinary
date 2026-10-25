import type { FC } from 'react';
import { AlertCircle, Tag } from 'lucide-react';
import type { LoadedLanguage, VerifiedClaim } from '../../types/api';

interface FramingAnalyticsProps {
  loadedLanguage: LoadedLanguage;
  claims: VerifiedClaim[];
}

export const FramingAnalytics: FC<FramingAnalyticsProps> = ({
  loadedLanguage,
  claims,
}) => {
  const framingClaims = claims.filter(
    (c) => c.framing_analysis && c.framing_analysis.is_misleading
  );
  const framingRate =
    claims.length > 0 ? Math.round((framingClaims.length / claims.length) * 100) : 0;

  const claimMarkers = new Set<string>();
  framingClaims.forEach((c) => {
    (c.framing_analysis?.detected_markers || []).forEach((m) => claimMarkers.add(m));
  });

  const allWords = Array.from(
    new Set([...loadedLanguage.detected_words, ...Array.from(claimMarkers)])
  );

  const isLoaded = loadedLanguage.density_pct > 3.0;

  return (
    <div className="editorial-card rounded-md p-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-stone-700" />
          <span className="text-xs font-mono-data uppercase font-bold tracking-wider text-stone-900">
            Rhetorical Framing & Lexical Spin
          </span>
        </div>

        <span
          className={`px-2 py-0.5 rounded text-xs font-mono-data font-semibold border ${
            isLoaded
              ? 'bg-amber-50 text-amber-900 border-amber-200'
              : 'bg-emerald-50 text-emerald-900 border-emerald-200'
          }`}
        >
          {loadedLanguage.density_pct.toFixed(2)}% Loaded Density
        </span>
      </div>

      {/* Numerical Ledger */}
      <div className="grid grid-cols-3 gap-2.5 mb-4 text-center font-mono-data">
        <div className="p-2.5 bg-stone-50 rounded border border-stone-200/80">
          <div className="text-xl font-bold text-stone-900">
            {loadedLanguage.loaded_count}
          </div>
          <div className="text-[10px] text-stone-500 uppercase mt-0.5">
            Loaded Terms
          </div>
        </div>

        <div className="p-2.5 bg-stone-50 rounded border border-stone-200/80">
          <div
            className={`text-xl font-bold ${
              framingRate > 0 ? 'text-amber-800' : 'text-emerald-800'
            }`}
          >
            {framingRate}%
          </div>
          <div className="text-[10px] text-stone-500 uppercase mt-0.5">
            Framing Skew Rate
          </div>
        </div>

        <div className="p-2.5 bg-stone-50 rounded border border-stone-200/80">
          <div className="text-xl font-bold text-stone-900">
            {allWords.length}
          </div>
          <div className="text-[10px] text-stone-500 uppercase mt-0.5">
            Flagged Markers
          </div>
        </div>
      </div>

      {/* Flagged Vocabulary */}
      <div>
        <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono-data font-bold text-stone-400 tracking-wider mb-2">
          <Tag className="w-3 h-3 text-stone-400" />
          <span>Sensational / Pejorative Terms Flagged in Text</span>
        </div>

        {allWords.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {allWords.map((word, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded text-xs font-mono-data bg-amber-50 text-amber-900 border border-amber-200 font-medium"
              >
                "{word}"
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-stone-500 italic font-sans">
            No emotionally charged or sensational rhetoric detected against lexicon baseline.
          </p>
        )}
      </div>
    </div>
  );
};
