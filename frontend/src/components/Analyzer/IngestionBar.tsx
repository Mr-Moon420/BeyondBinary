import type { FC } from 'react';
import { Link2, FileText, ArrowRight, Loader2, X } from 'lucide-react';

interface IngestionBarProps {
  url: string;
  onChangeUrl: (url: string) => void;
  onFetchUrl: () => void;
  isFetchingUrl: boolean;
  inputMode: 'url' | 'paste';
  onChangeMode: (mode: 'url' | 'paste') => void;
  articleMeta?: { title?: string; domain?: string; wordCount?: number; contentKind?: string } | null;
}

export const IngestionBar: FC<IngestionBarProps> = ({
  url,
  onChangeUrl,
  onFetchUrl,
  isFetchingUrl,
  inputMode,
  onChangeMode,
  articleMeta,
}) => {
  return (
    <div className="editorial-card rounded-md p-4 mb-6">
      {/* Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-1 bg-stone-100 p-1 rounded">
          <button
            onClick={() => onChangeMode('url')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all ${
              inputMode === 'url'
                ? 'bg-white text-stone-900 shadow-xs'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            <Link2 className="w-3.5 h-3.5" />
            <span>Article URL Link</span>
          </button>

          <button
            onClick={() => onChangeMode('paste')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all ${
              inputMode === 'paste'
                ? 'bg-white text-stone-900 shadow-xs'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Raw Text Manuscript</span>
          </button>
        </div>

        {articleMeta && articleMeta.wordCount ? (
          <span className="text-xs font-mono-data text-stone-600 bg-stone-100 px-2.5 py-0.5 rounded border border-stone-200">
            {articleMeta.contentKind === 'indexed_excerpt' ? 'Indexed excerpt · ' : ''}{articleMeta.wordCount} words extracted
          </span>
        ) : null}
      </div>

      {/* URL Input */}
      {inputMode === 'url' && (
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Link2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="url"
              value={url}
              onChange={(e) => onChangeUrl(e.target.value)}
              placeholder="Paste article URL (e.g. https://www.thehindu.com/... or https://www.reuters.com/...)"
              className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-stone-50 border border-stone-300 rounded text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-stone-800 font-sans"
              onKeyDown={(e) => {
                if (e.key === 'Enter') onFetchUrl();
              }}
            />
            {url && (
              <button
                onClick={() => onChangeUrl('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <button
            onClick={onFetchUrl}
            disabled={!url.trim() || isFetchingUrl}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded text-xs font-semibold bg-stone-900 hover:bg-stone-800 text-white transition-colors disabled:opacity-50"
          >
            {isFetchingUrl ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Fetching Content...</span>
              </>
            ) : (
              <>
                <span>Extract Text</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
