import type { FC } from 'react';
import { ArrowRight, Clock, ExternalLink, GitCompare } from 'lucide-react';
import type { TrendingArticle } from '../../types/api';
import { getBiasBadgeColor } from '../../utils/helpers';

interface ArticleCardProps {
  article: TrendingArticle;
  onAnalyze: (article: TrendingArticle) => void;
  onCompare?: (article: TrendingArticle) => void;
}

export const ArticleCard: FC<ArticleCardProps> = ({ article, onAnalyze, onCompare }) => {
  const biasColors = getBiasBadgeColor(article.publisher.bias);

  // Clean raw HTML entities and tags
  const cleanSnippet = (article.snippet || '')
    .replace(/&nbsp;/g, ' ')
    .replace(/<[^>]*>?/gm, '')
    .trim();

  // Format relative timestamp (e.g., "2h ago", "45m ago", "Just now")
  const formattedAge = (() => {
    if (!article.age) return '';
    try {
      const d = new Date(article.age);
      if (!isNaN(d.getTime())) {
        const diffMs = Date.now() - d.getTime();
        if (diffMs >= 0) {
          if (diffMs < 60 * 1000) return 'Just now';
          if (diffMs < 3600 * 1000) return `${Math.floor(diffMs / 60000)}m ago`;
          if (diffMs < 24 * 3600 * 1000) return `${Math.floor(diffMs / 3600000)}h ago`;
          if (diffMs < 7 * 24 * 3600 * 1000) return `${Math.floor(diffMs / 86400000)}d ago`;
        }
        return d.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      }
    } catch {
      return '';
    }
    return '';
  })();

  return (
    <article
      onClick={() => onAnalyze(article)}
      className="group flex flex-col justify-between p-5 bg-[#FFFFFF] border border-[#E4E4E7] rounded-none hover:border-stone-800 transition-all cursor-pointer relative shadow-xs"
    >
      <div>
        {/* Publisher Dateline & Stance Badge */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="font-mono-data text-xs font-bold text-stone-900 uppercase tracking-wider">
              {article.publisher.name}
            </span>
            <span
              className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono-data font-semibold uppercase tracking-wider ${biasColors.bg} ${biasColors.text} ${biasColors.border} border`}
            >
              {article.publisher.bias}
            </span>
          </div>

          {formattedAge && (
            <div className="flex items-center gap-1 text-[11px] font-mono-data text-stone-400">
              <Clock className="w-3 h-3" />
              <span>{formattedAge}</span>
            </div>
          )}
        </div>

        {/* Editorial Headline */}
        <h3 className="font-editorial text-lg sm:text-xl font-bold text-stone-900 leading-snug group-hover:text-stone-700 transition-colors mb-2.5">
          {article.title}
        </h3>

        {/* Clean Journalistic Excerpt */}
        {cleanSnippet && (
          <p className="text-xs sm:text-[13px] text-stone-600 line-clamp-3 leading-relaxed mb-3 font-sans">
            {cleanSnippet}
          </p>
        )}

        {/* Multi-source wire coverage pills */}
        {article.perspectives && article.perspectives.length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-stone-100">
            <span className="text-[10px] font-mono-data uppercase tracking-wider text-stone-400 block mb-1.5 font-medium">
              Syndicated Coverage:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {article.perspectives.map((p, idx) => {
                const pColors = getBiasBadgeColor(p.bias);
                return (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono-data bg-stone-50 border border-stone-200 text-stone-700"
                    title={p.title}
                  >
                    <span>{p.source}</span>
                    {p.bias && p.bias !== 'Unrated' && (
                      <span className={`text-[9px] font-semibold ${pColors.text}`}>
                        • {p.bias}
                      </span>
                    )}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="pt-3 border-t border-stone-100 flex items-center justify-between mt-auto gap-2">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[11px] text-stone-500 hover:text-stone-900 transition-colors font-mono-data"
          onClick={(e) => e.stopPropagation()}
        >
          <span>Source</span>
          <ExternalLink className="w-3 h-3 opacity-60" />
        </a>

        <div className="flex items-center gap-2">
          {onCompare && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCompare(article);
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-stone-100 hover:bg-stone-200 text-stone-800 transition-colors border border-stone-300 font-mono-data cursor-pointer"
              title="Compare this article with another article about the same event"
            >
              <GitCompare className="w-3.5 h-3.5 text-stone-600" />
              <span>Compare</span>
            </button>
          )}

          <button
            onClick={() => onAnalyze(article)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-stone-900 hover:bg-stone-800 text-white transition-colors cursor-pointer"
          >
            <span>Audit</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </div>
    </article>
  );
};
