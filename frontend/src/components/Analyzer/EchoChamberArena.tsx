import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  GitCompare,
  Flame,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ExternalLink,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Scale
} from 'lucide-react';
import type { CompareResponse, CompareRequest, VerifiedClaim } from '../../types/api';
import { comparePerspectives } from '../../services/api';

interface EchoChamberArenaProps {
  initialPerspectiveA?: { url?: string; title?: string; source?: string };
  initialPerspectiveB?: { url?: string; title?: string; source?: string };
  onBackToWire?: () => void;
}

export const EchoChamberArena: FC<EchoChamberArenaProps> = ({
  initialPerspectiveA,
  initialPerspectiveB,
  onBackToWire,
}) => {
  const [urlA, setUrlA] = useState(initialPerspectiveA?.url || '');
  const [titleA, setTitleA] = useState(initialPerspectiveA?.title || '');
  const [sourceA, setSourceA] = useState(initialPerspectiveA?.source || '');

  const [urlB, setUrlB] = useState(initialPerspectiveB?.url || '');
  const [titleB, setTitleB] = useState(initialPerspectiveB?.title || '');
  const [sourceB, setSourceB] = useState(initialPerspectiveB?.source || '');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<CompareResponse | null>(null);

  // If initial perspectives were provided from the Wire, auto-trigger comparison
  useEffect(() => {
    if (initialPerspectiveA?.url && initialPerspectiveB?.url) {
      handleRunComparison();
    }
  }, []);

  const handleRunComparison = async () => {
    if (!urlA.trim() && !titleA.trim()) {
      setError('Please provide at least a URL or title for Source A.');
      return;
    }
    if (!urlB.trim() && !titleB.trim()) {
      setError('Please provide at least a URL or title for Source B.');
      return;
    }

    setIsLoading(true);
    setError(null);

    const payload: CompareRequest = {
      url_a: urlA.trim() || undefined,
      title_a: titleA.trim() || undefined,
      source_a: sourceA.trim() || undefined,
      url_b: urlB.trim() || undefined,
      title_b: titleB.trim() || undefined,
      source_b: sourceB.trim() || undefined,
    };

    try {
      const res = await comparePerspectives(payload);
      setComparisonResult(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to execute cross-source comparison.');
    } finally {
      setIsLoading(false);
    }
  };

  const getVerdictBadge = (verdict: VerifiedClaim['verdict']) => {
    switch (verdict) {
      case 'Supported':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono-data bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" />
            Supported
          </span>
        );
      case 'Refuted':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono-data bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3" />
            Refuted
          </span>
        );
      case 'Misleading-Framing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono-data bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" />
            Misleading Framing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono-data bg-stone-50 text-stone-600 border border-stone-200">
            <HelpCircle className="w-3 h-3" />
            Context Needed
          </span>
        );
    }
  };

  const getBiasPill = (bias: string) => {
    const b = bias.toLowerCase();
    if (b.includes('left')) {
      return 'bg-blue-50 text-blue-800 border-blue-200';
    }
    if (b.includes('right')) {
      return 'bg-red-50 text-red-800 border-red-200';
    }
    return 'bg-stone-100 text-stone-800 border-stone-200';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
      {/* Header Deck */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-stone-200 gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono-data uppercase tracking-wider text-stone-500 mb-1">
            <Scale className="w-4 h-4 text-stone-700" />
            <span>Cross-Source Echo Chamber Arena</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-editorial font-bold text-stone-900">
            Multi-Perspective Framing & Polarization Matrix
          </h2>
          <p className="font-editorial italic text-stone-600 text-sm mt-1 max-w-2xl">
            Evaluate how distinct news organizations cover the exact same event. Compare ideological slant, rhetoric intensity, and selective fact patterns side-by-side.
          </p>
        </div>

        {onBackToWire && (
          <button
            onClick={onBackToWire}
            className="self-start md:self-auto px-3.5 py-1.5 text-xs font-mono-data border border-stone-300 rounded hover:bg-stone-100 transition-colors cursor-pointer text-stone-700"
          >
            ← Return to Wire Dispatch
          </button>
        )}
      </div>

      {/* Input Configuration Deck */}
      <div className="my-6 p-5 bg-white border border-stone-200 rounded-lg shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-stone-100">
          <div className="text-xs font-mono-data font-semibold uppercase tracking-wider text-stone-700">
            Source Configuration
          </div>
        </div>

        {/* Dual Input Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Source A Input */}
          <div className="p-3.5 bg-stone-50/60 rounded border border-stone-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono-data font-bold text-stone-800">
                PERSPECTIVE A (Left / Center)
              </span>
              <input
                type="text"
                placeholder="Outlet (e.g. CNN, MSNBC)"
                value={sourceA}
                onChange={(e) => setSourceA(e.target.value)}
                className="text-[11px] font-mono-data px-2 py-0.5 border border-stone-300 rounded bg-white w-40"
              />
            </div>
            <input
              type="text"
              placeholder="Article URL (optional)"
              value={urlA}
              onChange={(e) => setUrlA(e.target.value)}
              className="w-full text-xs font-mono-data px-2.5 py-1.5 border border-stone-300 rounded bg-white mb-2"
            />
            <input
              type="text"
              placeholder="Article Title or Core Framing"
              value={titleA}
              onChange={(e) => setTitleA(e.target.value)}
              className="w-full text-xs font-sans px-2.5 py-1.5 border border-stone-300 rounded bg-white"
            />
          </div>

          {/* Source B Input */}
          <div className="p-3.5 bg-stone-50/60 rounded border border-stone-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono-data font-bold text-stone-800">
                PERSPECTIVE B (Right / Center)
              </span>
              <input
                type="text"
                placeholder="Outlet (e.g. Fox News, WSJ)"
                value={sourceB}
                onChange={(e) => setSourceB(e.target.value)}
                className="text-[11px] font-mono-data px-2 py-0.5 border border-stone-300 rounded bg-white w-40"
              />
            </div>
            <input
              type="text"
              placeholder="Article URL (optional)"
              value={urlB}
              onChange={(e) => setUrlB(e.target.value)}
              className="w-full text-xs font-mono-data px-2.5 py-1.5 border border-stone-300 rounded bg-white mb-2"
            />
            <input
              type="text"
              placeholder="Article Title or Core Framing"
              value={titleB}
              onChange={(e) => setTitleB(e.target.value)}
              className="w-full text-xs font-sans px-2.5 py-1.5 border border-stone-300 rounded bg-white"
            />
          </div>
        </div>

        {/* Submit Bar */}
        <div className="mt-4 flex items-center justify-between pt-3 border-t border-stone-100">
          {error && <span className="text-xs text-rose-600 font-mono-data">{error}</span>}
          {!error && (
            <span className="text-[11px] text-stone-500 font-mono-data">
              Runs ClaimBuster DeBERTa + RoBERTa MNLI + Bias BERT on both articles simultaneously.
            </span>
          )}

          <button
            onClick={handleRunComparison}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-5 py-2 rounded bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold font-mono-data tracking-wider uppercase transition-all disabled:opacity-50 cursor-pointer"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Deconstructing Perspectives...</span>
              </>
            ) : (
              <>
                <GitCompare className="w-3.5 h-3.5" />
                <span>Execute Cross-Source Audit</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Comparison Results Deck */}
      {comparisonResult && (
        <div className="space-y-6 mt-8 animate-fadeIn">
          {/* 1. Massive Polarization & Framing Synthesizer */}
          <div className="p-6 bg-white border border-stone-300 rounded-lg shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-200">
              <div>
                <div className="text-[10px] font-mono-data uppercase tracking-widest text-stone-500 mb-1">
                  Echo-Chamber Metric
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-3xl font-editorial font-bold text-stone-950">
                    Polarization Index: {comparisonResult.comparison.polarization_score}%
                  </span>
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-mono-data font-bold uppercase tracking-wider ${
                      comparisonResult.comparison.polarization_score >= 55
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : comparisonResult.comparison.polarization_score >= 25
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}
                  >
                    {comparisonResult.comparison.divergence_level}
                  </span>
                </div>
              </div>

              {/* Stance Delta Pill */}
              <div className="text-right font-mono-data text-xs text-stone-600 bg-stone-50 px-3 py-2 rounded border border-stone-200">
                <div>Stance Shift: <span className="font-bold text-stone-900">{comparisonResult.comparison.stance_divergence_pct}%</span></div>
                <div>Rhetoric Disparity: <span className="font-bold text-stone-900">{comparisonResult.comparison.rhetoric_contrast.density_diff}%</span></div>
              </div>
            </div>

            {/* Polarization Bar */}
            <div className="my-4">
              <div className="w-full h-3 bg-stone-100 rounded-full overflow-hidden border border-stone-200 flex">
                <div
                  className={`h-full transition-all duration-700 ${
                    comparisonResult.comparison.polarization_score >= 55
                      ? 'bg-rose-500'
                      : comparisonResult.comparison.polarization_score >= 25
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, comparisonResult.comparison.polarization_score))}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono-data text-stone-400 mt-1">
                <span>0% Full Consensus</span>
                <span>50% Distinct Editorial Emphasis</span>
                <span>100% Opposing Polarized Narratives</span>
              </div>
            </div>

            {/* Editorial Synthesis Box */}
            <div className="p-3.5 bg-stone-50 rounded border border-stone-200 flex items-start gap-3">
              <Sparkles className="w-4 h-4 text-stone-700 shrink-0 mt-0.5" />
              <div className="text-xs font-sans text-stone-800 leading-relaxed">
                <span className="font-mono-data uppercase text-[10px] font-bold tracking-wider text-stone-500 block mb-0.5">
                  Comparative Editorial Synthesis:
                </span>
                {comparisonResult.comparison.editorial_synthesis}
              </div>
            </div>
          </div>

          {/* 2. Side-by-Side Dual Deck */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* OUTLET A CARD */}
            <div className="bg-white border border-stone-300 rounded-lg shadow-sm flex flex-col overflow-hidden">
              {/* Outlet Header */}
              <div className="p-4 bg-stone-50 border-b border-stone-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block">
                    Outlet A Perspective
                  </span>
                  <h3 className="font-editorial text-xl font-bold text-stone-900">
                    {comparisonResult.outlet_a.source_name}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-mono-data font-bold border ${getBiasPill(
                      comparisonResult.outlet_a.bias_analysis.bias_label
                    )}`}
                  >
                    {comparisonResult.outlet_a.bias_analysis.bias_label}
                  </span>
                  <div className="text-right font-mono-data text-xs">
                    <span className="text-stone-400 block text-[9px]">CREDIBILITY</span>
                    <span className="font-bold text-stone-900">
                      {comparisonResult.outlet_a.credibility_score}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Title & Headline Framing */}
              <div className="p-4 border-b border-stone-100">
                <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block mb-1">
                  Reported Headline:
                </span>
                <p className="font-editorial font-bold text-base text-stone-900 leading-snug">
                  "{comparisonResult.outlet_a.title}"
                </p>
                {comparisonResult.outlet_a.source_url && (
                  <a
                    href={comparisonResult.outlet_a.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-mono-data text-stone-500 hover:text-stone-800 mt-2"
                  >
                    <span>View original link</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                )}
              </div>

              {/* Rhetoric & Sensationalism Box */}
              <div className="p-4 border-b border-stone-100 bg-stone-50/40">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono-data font-semibold text-stone-700 flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5 text-amber-600" />
                    <span>Sensationalism Density:</span>
                  </span>
                  <span className="font-mono-data text-xs font-bold text-stone-900">
                    {comparisonResult.outlet_a.bias_analysis.loaded_language.density_pct}%
                  </span>
                </div>
                {(comparisonResult.outlet_a.bias_analysis.loaded_language.detected_words?.length || comparisonResult.outlet_a.bias_analysis.loaded_language.loaded_words?.length || 0) > 0 ? (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {(comparisonResult.outlet_a.bias_analysis.loaded_language.detected_words || comparisonResult.outlet_a.bias_analysis.loaded_language.loaded_words || []).slice(0, 8).map((w, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono-data bg-amber-50 text-amber-800 border border-amber-200"
                      >
                        {w}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-stone-500 italic font-mono-data">
                    No inflammatory or loaded lexical markers detected.
                  </p>
                )}
              </div>

              {/* Key Verified Claims */}
              <div className="p-4 flex-1">
                <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block mb-2 font-medium">
                  Verified Factual Claims:
                </span>
                {comparisonResult.outlet_a.claims.length > 0 ? (
                  <div className="space-y-3">
                    {comparisonResult.outlet_a.claims.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-stone-50 rounded border border-stone-200 text-xs font-sans leading-relaxed"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          {getVerdictBadge(c.verdict)}
                          <span className="text-[10px] font-mono-data text-stone-500">
                            {c.retrieval_source}
                          </span>
                        </div>
                        <p className="text-stone-800">{c.claim}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-stone-500 italic">No discrete claims isolated.</p>
                )}
              </div>
            </div>

            {/* OUTLET B CARD */}
            <div className="bg-white border border-stone-300 rounded-lg shadow-sm flex flex-col overflow-hidden">
              {/* Outlet Header */}
              <div className="p-4 bg-stone-50 border-b border-stone-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block">
                    Outlet B Perspective
                  </span>
                  <h3 className="font-editorial text-xl font-bold text-stone-900">
                    {comparisonResult.outlet_b.source_name}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-mono-data font-bold border ${getBiasPill(
                      comparisonResult.outlet_b.bias_analysis.bias_label
                    )}`}
                  >
                    {comparisonResult.outlet_b.bias_analysis.bias_label}
                  </span>
                  <div className="text-right font-mono-data text-xs">
                    <span className="text-stone-400 block text-[9px]">CREDIBILITY</span>
                    <span className="font-bold text-stone-900">
                      {comparisonResult.outlet_b.credibility_score}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Title & Headline Framing */}
              <div className="p-4 border-b border-stone-100">
                <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block mb-1">
                  Reported Headline:
                </span>
                <p className="font-editorial font-bold text-base text-stone-900 leading-snug">
                  "{comparisonResult.outlet_b.title}"
                </p>
                {comparisonResult.outlet_b.source_url && (
                  <a
                    href={comparisonResult.outlet_b.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-mono-data text-stone-500 hover:text-stone-800 mt-2"
                  >
                    <span>View original link</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                )}
              </div>

              {/* Rhetoric & Sensationalism Box */}
              <div className="p-4 border-b border-stone-100 bg-stone-50/40">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono-data font-semibold text-stone-700 flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5 text-amber-600" />
                    <span>Sensationalism Density:</span>
                  </span>
                  <span className="font-mono-data text-xs font-bold text-stone-900">
                    {comparisonResult.outlet_b.bias_analysis.loaded_language.density_pct}%
                  </span>
                </div>
                {(comparisonResult.outlet_b.bias_analysis.loaded_language.detected_words?.length || comparisonResult.outlet_b.bias_analysis.loaded_language.loaded_words?.length || 0) > 0 ? (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {(comparisonResult.outlet_b.bias_analysis.loaded_language.detected_words || comparisonResult.outlet_b.bias_analysis.loaded_language.loaded_words || []).slice(0, 8).map((w, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono-data bg-amber-50 text-amber-800 border border-amber-200"
                      >
                        {w}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-stone-500 italic font-mono-data">
                    No inflammatory or loaded lexical markers detected.
                  </p>
                )}
              </div>

              {/* Key Verified Claims */}
              <div className="p-4 flex-1">
                <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block mb-2 font-medium">
                  Verified Factual Claims:
                </span>
                {comparisonResult.outlet_b.claims.length > 0 ? (
                  <div className="space-y-3">
                    {comparisonResult.outlet_b.claims.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-stone-50 rounded border border-stone-200 text-xs font-sans leading-relaxed"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          {getVerdictBadge(c.verdict)}
                          <span className="text-[10px] font-mono-data text-stone-500">
                            {c.retrieval_source}
                          </span>
                        </div>
                        <p className="text-stone-800">{c.claim}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-stone-500 italic">No discrete claims isolated.</p>
                )}
              </div>
            </div>
          </div>

          {/* 3. Cross-Source Contrast Matrix (Bottom Bar) */}
          <div className="p-5 bg-white border border-stone-200 rounded-lg flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-stone-800 shrink-0" />
              <div className="text-xs font-sans text-stone-700">
                <span className="font-bold text-stone-900 block font-mono-data uppercase text-[11px]">
                  Evaluation Takeaway:
                </span>
                Both outlets present factual assertions, but divergent editorial framing creates an informational echo chamber.
              </div>
            </div>

            <button
              onClick={() => window.print()}
              className="px-4 py-2 border border-stone-300 rounded text-xs font-mono-data text-stone-800 hover:bg-stone-50 transition-colors cursor-pointer shrink-0"
            >
              Print Comparison Dossier
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
