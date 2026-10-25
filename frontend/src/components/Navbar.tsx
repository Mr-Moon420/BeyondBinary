import type { FC } from 'react';
import { Newspaper, SearchCode, GitCompare } from 'lucide-react';

interface NavbarProps {
  activeTab: 'trending' | 'analyzer' | 'compare';
  onSelectTab: (tab: 'trending' | 'analyzer' | 'compare') => void;
  isBackendHealthy?: boolean;
}

export const Navbar: FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
}) => {
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <header className="w-full bg-[#FFFFFF] border-b border-[#E4E4E7]">
      {/* Top Dateline Bar */}
      <div className="border-b border-[#F4F4F5] bg-[#FBFBFA] px-4 sm:px-8 py-1.5 text-[11px] font-mono-data text-stone-500">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-stone-800">Media Observatory</span>
            <span className="text-stone-300">•</span>
            <span>{currentDate}</span>
          </div>
        </div>
      </div>

      {/* Editorial Masthead */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6 text-center">
        <div className="text-[11px] uppercase tracking-[0.25em] font-mono-data text-stone-500 mb-1">
          Explainable Fact-Checking & Stance Detection System
        </div>
        <h1 className="text-3xl sm:text-5xl font-editorial font-bold tracking-tight text-stone-900 leading-none">
          BEYOND BINARY
        </h1>
        <p className="font-editorial italic text-stone-600 text-sm sm:text-base mt-2 max-w-xl mx-auto">
          Moving beyond “Real or Fake” to evidence-grounded credibility indices, ideological spectrum analysis, and rhetorical framing scrutiny.
        </p>
      </div>

      {/* Navigation Desk Bar */}
      <div className="border-t border-[#E4E4E7] bg-[#FFFFFF]">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 flex items-center justify-between">
          <nav className="flex items-center gap-1">
            <button
              onClick={() => onSelectTab('trending')}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
                activeTab === 'trending'
                  ? 'border-stone-900 text-stone-950 bg-stone-50/50'
                  : 'border-transparent text-stone-500 hover:text-stone-800 hover:bg-stone-50/30'
              }`}
            >
              <Newspaper className="w-3.5 h-3.5" />
              <span>The News Wire</span>
            </button>

            <button
              onClick={() => onSelectTab('analyzer')}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
                activeTab === 'analyzer'
                  ? 'border-stone-900 text-stone-950 bg-stone-50/50'
                  : 'border-transparent text-stone-500 hover:text-stone-800 hover:bg-stone-50/30'
              }`}
            >
              <SearchCode className="w-3.5 h-3.5" />
              <span>The Audit Desk</span>
            </button>

            <button
              onClick={() => onSelectTab('compare')}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
                activeTab === 'compare'
                  ? 'border-stone-900 text-stone-950 bg-stone-50/50'
                  : 'border-transparent text-stone-500 hover:text-stone-800 hover:bg-stone-50/30'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span>Echo-Chamber Deck</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[9px] font-mono-data bg-stone-100 border border-stone-200 text-stone-600">
                Compare
              </span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};
