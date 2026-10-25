import { useState, useEffect, useMemo, type FC } from 'react';
import {
  RotateCw,
  Search,
  SlidersHorizontal,
  AlertTriangle,
  FileQuestion,
  ChevronDown,
} from 'lucide-react';
import type { TrendingArticle } from '../../types/api';
import { fetchTrendingFeed } from '../../services/api';
import { ArticleCard } from './ArticleCard';

interface TrendingWireProps {
  onSelectArticle: (article: TrendingArticle) => void;
  onCompareArticle?: (article: TrendingArticle) => void;
}

export type TopicKey = 'politics' | 'tech' | 'business' | 'world' | 'sports';

const TOPIC_TABS: { key: TopicKey; label: string }[] = [
  { key: 'politics', label: 'Politics & Policy' },
  { key: 'tech', label: 'Tech & AI' },
  { key: 'business', label: 'Markets & Economy' },
  { key: 'world', label: 'World Dispatch' },
  { key: 'sports', label: 'Sports & Culture' },
];

export const TrendingWire: FC<TrendingWireProps> = ({ onSelectArticle, onCompareArticle }) => {
  const [topic, setTopic] = useState<TopicKey>('politics');
  const [articles, setArticles] = useState<Record<string, TrendingArticle[]>>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [biasFilter, setBiasFilter] = useState<string>('all');
  const [displayCount, setDisplayCount] = useState<number>(12);

  const loadFeed = async (selectedTopic?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchTrendingFeed(selectedTopic || topic);
      setArticles((prev) => ({
        ...prev,
        ...data.topics,
      }));
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve newsfeed.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setDisplayCount(12);
    if (!articles[topic] || articles[topic].length === 0) {
      loadFeed(topic);
    }
  }, [topic]);

  const currentArticles = useMemo(() => {
    const list = articles[topic] || [];
    return list.filter((a) => {
      const matchesSearch =
        searchQuery === '' ||
        a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.publisher.name.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesBias =
        biasFilter === 'all' ||
        (biasFilter === 'left' && (a.publisher.bias === 'Left' || a.publisher.bias === 'Lean Left')) ||
        (biasFilter === 'center' && a.publisher.bias === 'Center') ||
        (biasFilter === 'right' && (a.publisher.bias === 'Right' || a.publisher.bias === 'Lean Right'));

      return matchesSearch && matchesBias;
    });
  }, [articles, topic, searchQuery, biasFilter]);

  const visibleArticles = useMemo(() => {
    return currentArticles.slice(0, displayCount);
  }, [currentArticles, displayCount]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-stone-300 mb-6">
        <div>
          <span className="text-[11px] font-mono-data uppercase tracking-[0.2em] text-stone-500 font-semibold block mb-1">
            Global Syndicated Desks
          </span>
          <h2 className="text-2xl sm:text-3xl font-editorial font-bold text-stone-900">
            Real-Time Wire Dispatch
          </h2>
        </div>

        <button
          onClick={() => loadFeed()}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded border border-stone-300 bg-white hover:bg-stone-50 text-xs font-semibold text-stone-700 transition-colors self-start sm:self-auto disabled:opacity-50"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Feeds</span>
        </button>
      </div>

      {/* Editorial Filter Strip */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-stone-200 p-3 rounded-md mb-8 shadow-xs">
        {/* Category Tabs */}
        <div className="flex flex-wrap items-center gap-1">
          {TOPIC_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTopic(tab.key)}
              className={`px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-wider transition-all ${
                topic === tab.key
                  ? 'bg-stone-900 text-white shadow-xs'
                  : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Ideological Alignment */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by publication or title..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-stone-50 border border-stone-200 rounded text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-stone-500 font-sans"
            />
          </div>

          <div className="flex items-center gap-1 border-l border-stone-200 pl-3 text-xs font-mono-data">
            <SlidersHorizontal className="w-3.5 h-3.5 text-stone-400" />
            <span className="text-stone-500 text-[11px] uppercase mr-1">Bias:</span>
            {(['all', 'left', 'center', 'right'] as const).map((b) => (
              <button
                key={b}
                onClick={() => setBiasFilter(b)}
                className={`px-2 py-0.5 rounded text-[11px] uppercase font-semibold transition-colors ${
                  biasFilter === b
                    ? 'bg-stone-800 text-white'
                    : 'text-stone-500 hover:text-stone-900 hover:bg-stone-100'
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-md border border-rose-200 bg-rose-50 text-rose-900 text-xs flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-700" />
            <span>Feed could not be retrieved: {error}</span>
          </div>
          <button
            onClick={() => loadFeed(topic)}
            className="px-2.5 py-1 bg-rose-100 hover:bg-rose-200 text-rose-950 font-semibold rounded font-mono-data text-[11px]"
          >
            Retry
          </button>
        </div>
      )}

      {/* Grid of Articles */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((idx) => (
            <div key={idx} className="editorial-card rounded-md p-6 h-64 animate-pulse flex flex-col justify-between">
              <div>
                <div className="h-3 w-28 bg-stone-200 rounded mb-4" />
                <div className="h-5 w-full bg-stone-200 rounded mb-2" />
                <div className="h-5 w-3/4 bg-stone-200 rounded mb-4" />
                <div className="h-3 w-full bg-stone-100 rounded mb-1.5" />
                <div className="h-3 w-5/6 bg-stone-100 rounded" />
              </div>
              <div className="pt-3 border-t border-stone-100 flex justify-between">
                <div className="h-4 w-20 bg-stone-200 rounded" />
                <div className="h-7 w-24 bg-stone-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : currentArticles.length > 0 ? (
        <>
          <div className="flex items-center justify-between text-xs text-stone-500 font-mono-data mb-4 px-1">
            <span>
              Dispatches: <strong className="text-stone-800">{visibleArticles.length}</strong> of {currentArticles.length} active stories
            </span>
            <span className="text-[11px] text-stone-400 hidden sm:inline">
              Real-time Syndicated Wire • AllSides Media Intelligence
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visibleArticles.map((article, i) => (
              <ArticleCard
                key={`${article.url}-${i}`}
                article={article}
                onAnalyze={onSelectArticle}
                onCompare={onCompareArticle}
              />
            ))}
          </div>

          {currentArticles.length > displayCount && (
            <div className="flex justify-center mt-10">
              <button
                onClick={() => setDisplayCount((prev) => prev + 6)}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md border border-stone-300 bg-white hover:bg-stone-50 text-xs font-semibold text-stone-800 transition-all shadow-xs hover:border-stone-400 font-mono-data uppercase tracking-wider cursor-pointer"
              >
                <span>Load More Wire Stories ({currentArticles.length - displayCount} remaining)</span>
                <ChevronDown className="w-3.5 h-3.5 text-stone-500" />
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="editorial-card rounded-md p-12 text-center max-w-md mx-auto my-12">
          <FileQuestion className="w-10 h-10 text-stone-400 mx-auto mb-3" />
          <h3 className="font-editorial text-lg font-bold text-stone-900 mb-1">
            No Dispatches Match Criteria
          </h3>
          <p className="text-xs text-stone-500 mb-4 font-sans">
            Clear your search term or select "ALL" in the bias filter to view full syndicated headlines.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setBiasFilter('all');
            }}
            className="text-xs font-semibold text-stone-900 underline font-mono-data"
          >
            Clear Search & Filters
          </button>
        </div>
      )}
    </div>
  );
};
