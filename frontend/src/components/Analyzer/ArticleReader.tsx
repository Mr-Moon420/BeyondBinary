import { useState, useMemo, type FC } from 'react';
import {
  RotateCcw,
  FileText,
  Globe,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Eye,
  Edit3,
  Flame,
  Sparkles,
  X
} from 'lucide-react';
import type { VerifiedClaim } from '../../types/api';

interface ArticleReaderProps {
  text: string;
  onChangeText: (text: string) => void;
  onAnalyze: () => void;
  onReset: () => void;
  isAnalyzing: boolean;
  claims: VerifiedClaim[];
  loadedWords: string[];
  articleTitle?: string;
  sourceDomain?: string;
  sourceUrl?: string;
  isFetchingUrl?: boolean;
}

export const ArticleReader: FC<ArticleReaderProps> = ({
  text,
  onChangeText,
  onAnalyze,
  onReset,
  isAnalyzing,
  claims,
  loadedWords,
  articleTitle,
  sourceDomain,
  sourceUrl,
  isFetchingUrl = false,
}) => {
  // If claims exist, default to 'inspector' mode; otherwise 'editor'
  const [viewMode, setViewMode] = useState<'inspector' | 'editor'>('editor');
  const [selectedClaim, setSelectedClaim] = useState<VerifiedClaim | null>(null);

  // Automatically switch to inspector mode once analysis produces claims
  useMemo(() => {
    if (claims.length > 0) {
      setViewMode('inspector');
    }
  }, [claims.length]);

  // Breakdown counts
  const supportedCount = claims.filter((c) => c.verdict === 'Supported').length;
  const contextCount = claims.filter((c) => c.verdict === 'Not Enough Info').length;
  const refutedCount = claims.filter((c) => c.verdict === 'Refuted' || c.verdict === 'Misleading-Framing').length;

  // Normalized claim map for fast matching
  const claimMap = useMemo(() => {
    const map = new Map<string, VerifiedClaim>();
    claims.forEach((c) => {
      // Store clean stripped version
      map.set(c.claim.trim().toLowerCase(), c);
    });
    return map;
  }, [claims]);

  const loadedWordSet = useMemo(() => {
    return new Set(loadedWords.map((w) => w.toLowerCase()));
  }, [loadedWords]);

  const getVerdictStyle = (verdict: VerifiedClaim['verdict']) => {
    switch (verdict) {
      case 'Supported':
        return {
          bg: 'bg-emerald-100/70 hover:bg-emerald-200/80 text-emerald-950 border-b-2 border-emerald-600',
          badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />,
          label: 'Supported',
        };
      case 'Refuted':
        return {
          bg: 'bg-rose-100/70 hover:bg-rose-200/80 text-rose-950 border-b-2 border-rose-600',
          badgeBg: 'bg-rose-100 text-rose-800 border-rose-300',
          icon: <XCircle className="w-3.5 h-3.5 text-rose-700" />,
          label: 'Refuted',
        };
      case 'Misleading-Framing':
        return {
          bg: 'bg-amber-100/70 hover:bg-amber-200/80 text-amber-950 border-b-2 border-amber-500',
          badgeBg: 'bg-amber-100 text-amber-800 border-amber-300',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />,
          label: 'Misleading Framing',
        };
      default:
        return {
          bg: 'bg-stone-200/60 hover:bg-stone-300/60 text-stone-900 border-b-2 border-stone-400',
          badgeBg: 'bg-stone-100 text-stone-700 border-stone-300',
          icon: <HelpCircle className="w-3.5 h-3.5 text-stone-600" />,
          label: 'Context Needed',
        };
    }
  };

  /**
   * Renders a paragraph by matching claims and loaded rhetoric keywords.
   */
  const renderAnnotatedParagraph = (paragraphText: string, pIdx: number) => {
    if (!paragraphText.trim()) return null;

    // Check if any claim is directly inside this paragraph
    const matchedClaimsInParagraph: { start: number; end: number; claimObj: VerifiedClaim }[] = [];

    claims.forEach((c) => {
      const idx = paragraphText.indexOf(c.claim);
      if (idx !== -1) {
        matchedClaimsInParagraph.push({
          start: idx,
          end: idx + c.claim.length,
          claimObj: c,
        });
      }
    });

    // If no exact match, fallback to fuzzy sentence matching
    if (matchedClaimsInParagraph.length === 0) {
      // Simple sentence regex split
      const sentences = paragraphText.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) || [paragraphText];
      return (
        <p key={pIdx} className="mb-4 leading-relaxed font-sans text-stone-800 text-[14px]">
          {sentences.map((sent, sIdx) => {
            const cleanSent = sent.trim().toLowerCase();
            const matched = claimMap.get(cleanSent);

            if (matched) {
              const style = getVerdictStyle(matched.verdict);
              const isSelected = selectedClaim?.claim === matched.claim;
              return (
                <span
                  key={sIdx}
                  onClick={() => setSelectedClaim(matched)}
                  className={`cursor-pointer transition-all px-1 py-0.5 rounded-sm mx-0.5 ${style.bg} ${
                    isSelected ? 'ring-2 ring-stone-800 ring-offset-1 font-medium' : ''
                  }`}
                  title={`Click to inspect verification evidence: ${style.label}`}
                >
                  {sent}
                </span>
              );
            }

            // Highlight individual loaded words inside the sentence
            return (
              <span key={sIdx}>
                {sent.split(/\b/).map((tok, tokIdx) => {
                  if (loadedWordSet.has(tok.toLowerCase())) {
                    return (
                      <span
                        key={tokIdx}
                        className="bg-amber-100/90 text-amber-900 font-semibold underline decoration-wavy decoration-amber-500 px-0.5 rounded-xs"
                        title={`Flagged loaded keyword: "${tok}"`}
                      >
                        {tok}
                      </span>
                    );
                  }
                  return tok;
                })}
              </span>
            );
          })}
        </p>
      );
    }

    // Sort matched claim spans
    matchedClaimsInParagraph.sort((a, b) => a.start - b.start);

    // Build segments
    const elements = [];
    let lastIndex = 0;

    matchedClaimsInParagraph.forEach((match, mIdx) => {
      // Text before claim
      if (match.start > lastIndex) {
        const preText = paragraphText.substring(lastIndex, match.start);
        elements.push(
          <span key={`pre-${mIdx}`}>
            {preText.split(/\b/).map((tok, tIdx) => {
              if (loadedWordSet.has(tok.toLowerCase())) {
                return (
                  <span
                    key={tIdx}
                    className="bg-amber-100/90 text-amber-900 font-semibold underline decoration-wavy decoration-amber-500 px-0.5 rounded-xs"
                    title={`Flagged loaded keyword: "${tok}"`}
                  >
                    {tok}
                  </span>
                );
              }
              return tok;
            })}
          </span>
        );
      }

      // The claim itself
      const style = getVerdictStyle(match.claimObj.verdict);
      const isSelected = selectedClaim?.claim === match.claimObj.claim;
      elements.push(
        <span
          key={`claim-${mIdx}`}
          onClick={() => setSelectedClaim(match.claimObj)}
          className={`cursor-pointer transition-all px-1 py-0.5 rounded-sm mx-0.5 ${style.bg} ${
            isSelected ? 'ring-2 ring-stone-800 ring-offset-1 font-medium' : ''
          }`}
          title={`Click to inspect verification evidence: ${style.label}`}
        >
          {match.claimObj.claim}
        </span>
      );

      lastIndex = match.end;
    });

    // Remaining text after last claim
    if (lastIndex < paragraphText.length) {
      const postText = paragraphText.substring(lastIndex);
      elements.push(
        <span key="post">
          {postText.split(/\b/).map((tok, tIdx) => {
            if (loadedWordSet.has(tok.toLowerCase())) {
              return (
                <span
                  key={tIdx}
                  className="bg-amber-100/90 text-amber-900 font-semibold underline decoration-wavy decoration-amber-500 px-0.5 rounded-xs"
                  title={`Flagged loaded keyword: "${tok}"`}
                >
                  {tok}
                </span>
              );
            }
            return tok;
          })}
        </span>
      );
    }

    return (
      <p key={pIdx} className="mb-4 leading-relaxed font-sans text-stone-800 text-[14px]">
        {elements}
      </p>
    );
  };

  const paragraphs = useMemo(() => {
    return text.split(/\n\s*\n/).filter((p) => p.trim().length > 0);
  }, [text]);

  return (
    <div className="editorial-card rounded-md p-6 flex flex-col h-full bg-white border border-stone-200 shadow-sm relative">
      {/* Header Info & View Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-stone-200 mb-4 gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileText className="w-4 h-4 text-stone-700" />
            <span className="text-xs font-mono-data font-bold uppercase tracking-wider text-stone-900">
              Source Material Manuscript
            </span>

            {loadedWords.length > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-mono-data font-semibold flex items-center gap-1">
                <Flame className="w-3 h-3 text-amber-600" />
                <span>{loadedWords.length} loaded keywords</span>
              </span>
            )}
          </div>

          {articleTitle && (
            <h3 className="font-editorial text-base sm:text-lg font-bold text-stone-900 line-clamp-1">
              {articleTitle}
            </h3>
          )}
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {sourceDomain && (
            <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono-data bg-stone-100 text-stone-800 border border-stone-200">
              <Globe className="w-3 h-3 text-stone-500" />
              <span>{sourceDomain}</span>
            </span>
          )}

          <div className="inline-flex rounded-md border border-stone-300 p-0.5 bg-stone-100 text-xs font-mono-data">
            <button
              onClick={() => setViewMode('inspector')}
              disabled={claims.length === 0}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                viewMode === 'inspector'
                  ? 'bg-white font-bold text-stone-900 shadow-xs'
                  : 'text-stone-500 hover:text-stone-900 disabled:opacity-40 disabled:cursor-not-allowed'
              }`}
              title={claims.length === 0 ? 'Run audit first to enable highlighted inspector' : ''}
            >
              <Eye className="w-3 h-3" />
              <span>Inspector</span>
            </button>
            <button
              onClick={() => setViewMode('editor')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                viewMode === 'editor'
                  ? 'bg-white font-bold text-stone-900 shadow-xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              <Edit3 className="w-3 h-3" />
              <span>Source Text</span>
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Legend Bar (shown in inspector view when claims exist) */}
      {viewMode === 'inspector' && claims.length > 0 && (
        <div className="mb-4 p-2.5 bg-stone-50 rounded border border-stone-200 flex flex-wrap items-center justify-between gap-2 text-xs font-mono-data">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[10px] text-stone-400 uppercase tracking-wider font-semibold">
              Interactive Claim Highlights:
            </span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] bg-emerald-100/80 text-emerald-900 border border-emerald-300">
              <CheckCircle2 className="w-3 h-3 text-emerald-700" />
              <span>Supported ({supportedCount})</span>
            </span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] bg-stone-200/80 text-stone-800 border border-stone-300">
              <HelpCircle className="w-3 h-3 text-stone-600" />
              <span>Context Needed ({contextCount})</span>
            </span>
            {refutedCount > 0 && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] bg-rose-100/80 text-rose-900 border border-rose-300">
                <XCircle className="w-3 h-3 text-rose-700" />
                <span>Refuted / Slanted ({refutedCount})</span>
              </span>
            )}
          </div>

          <span className="text-[10px] text-stone-500 italic">
            Click any highlighted statement to inspect evidence.
          </span>
        </div>
      )}

      {/* Main Body Display */}
      <div className="relative flex-1 min-h-[380px] mb-4">
        {viewMode === 'inspector' && claims.length > 0 ? (
          <div className="w-full h-full p-5 rounded bg-stone-50/50 border border-stone-200 overflow-y-auto max-h-[500px]">
            {paragraphs.map((para, i) => renderAnnotatedParagraph(para, i))}
          </div>
        ) : (
          <textarea
            value={text}
            onChange={(e) => onChangeText(e.target.value)}
            placeholder="Paste full article text, news report, or factual assertions to begin decomposition..."
            className="w-full h-full p-4 rounded bg-stone-50 border border-stone-200 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-stone-800 text-sm leading-relaxed font-sans resize-y min-h-[360px]"
          />
        )}
      </div>

      {/* Floating Interactive Evidence Inspector Popover */}
      {selectedClaim && (
        <div className="mb-4 p-4 bg-white rounded-md border-2 border-stone-800 shadow-md animate-fadeIn">
          <div className="flex items-start justify-between gap-3 pb-2 border-b border-stone-200 mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-stone-800" />
              <span className="text-xs font-mono-data font-bold uppercase tracking-wider text-stone-900">
                Claim Verification Dossier
              </span>
            </div>

            <button
              onClick={() => setSelectedClaim(null)}
              className="text-stone-400 hover:text-stone-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Statement & Verdict */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
            <span
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono-data font-bold border ${
                getVerdictStyle(selectedClaim.verdict).badgeBg
              }`}
            >
              {getVerdictStyle(selectedClaim.verdict).icon}
              <span>{selectedClaim.verdict}</span>
              <span className="text-[10px] font-normal opacity-75">
                ({Math.round(selectedClaim.confidence * 100)}% confidence)
              </span>
            </span>

            <span className="text-[11px] font-mono-data text-stone-500">
              Source: <strong className="text-stone-800">{selectedClaim.retrieval_source}</strong>
            </span>
          </div>

          <p className="text-xs font-editorial font-bold text-stone-900 mb-2.5">
            "{selectedClaim.claim}"
          </p>

          {/* Corroborating Evidence Snippet */}
          {selectedClaim.evidence && (
            <div className="p-2.5 bg-stone-50 rounded border border-stone-200 text-[11px] font-sans text-stone-700 leading-relaxed">
              <span className="text-[9px] font-mono-data uppercase tracking-wider text-stone-400 block font-semibold mb-1">
                Corroborating Corpus Evidence:
              </span>
              <p className="line-clamp-3">
                {Array.isArray(selectedClaim.evidence)
                  ? selectedClaim.evidence[0] || 'No snippet text available.'
                  : selectedClaim.evidence}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-stone-200">
        <button
          onClick={onReset}
          disabled={!text && claims.length === 0}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono-data text-stone-500 hover:text-stone-900 transition-colors disabled:opacity-40 cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Desk</span>
        </button>

        <button
          onClick={onAnalyze}
          disabled={(!text.trim() && !sourceUrl?.trim()) || isAnalyzing || isFetchingUrl}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded text-xs sm:text-sm font-semibold bg-stone-900 hover:bg-stone-800 text-white transition-colors disabled:opacity-50 cursor-pointer"
        >
          {isFetchingUrl ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Extracting Article Text...</span>
            </>
          ) : isAnalyzing ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Deconstructing Article...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Deconstruct & Audit Claims</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
