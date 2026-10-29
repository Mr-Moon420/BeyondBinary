import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { TrendingWire } from './components/Trending/TrendingWire';
import { Workbench } from './components/Analyzer/Workbench';
import { EchoChamberArena } from './components/Analyzer/EchoChamberArena';
import type { TrendingArticle } from './types/api';
import { checkBackendHealth } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState<'trending' | 'analyzer' | 'compare'>('trending');
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(true);
  const [selectedArticle, setSelectedArticle] = useState<{
    url: string;
    title: string;
    snippet?: string;
  } | null>(null);

  const [compareData, setCompareData] = useState<{
    perspectiveA?: { url?: string; title?: string; source?: string };
    perspectiveB?: { url?: string; title?: string; source?: string };
  } | null>(null);

  useEffect(() => {
    const probe = async () => {
      const healthy = await checkBackendHealth();
      setIsBackendHealthy(healthy);
    };
    probe();
    const interval = setInterval(probe, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectArticleToAnalyze = (article: TrendingArticle) => {
    setSelectedArticle({
      url: article.url,
      title: article.title,
      snippet: article.snippet,
    });
    setActiveTab('analyzer');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleComparePerspectives = (article: TrendingArticle) => {
    const p = article.perspectives || [];
    const pA = { title: article.title, source: article.publisher.name, url: article.url };
    const pB = p.find(perspective => perspective.url && perspective.url !== article.url);

    setCompareData({
      perspectiveA: { url: pA.url, title: pA.title, source: pA.source },
      perspectiveB: pB ? { url: pB.url, title: pB.title, source: pB.source } : undefined,
    });
    setActiveTab('compare');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FBFBFA] text-[#18181B]">
      {/* Editorial Header */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'trending' ? (
          <TrendingWire
            onSelectArticle={handleSelectArticleToAnalyze}
            onCompareArticle={handleComparePerspectives}
          />
        ) : activeTab === 'analyzer' ? (
          <Workbench
            onResetContext={() => setSelectedArticle(null)}
            initialUrl={selectedArticle?.url}
            initialTitle={selectedArticle?.title}
            initialSnippet={selectedArticle?.snippet}
          />
        ) : (
          <EchoChamberArena
            initialPerspectiveA={compareData?.perspectiveA}
            initialPerspectiveB={compareData?.perspectiveB}
            onBackToWire={() => setActiveTab('trending')}
          />
        )}
      </main>

      {/* Editorial Broadsheet Colophon / Footer */}
      <footer className="border-t border-[#E4E4E7] bg-[#FFFFFF] py-6 px-4 sm:px-8 text-xs text-stone-500 font-mono-data mt-12">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-center md:text-left">
            <span className="font-bold text-stone-800">BEYOND BINARY</span> — Multi-Dimensional Media Credibility & Ideological Bias Analysis
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] text-stone-500 font-mono-data">
            <span>ClaimBuster DeBERTa-v2</span>
            <span>•</span>
            <span>RoBERTa-large-MNLI</span>
            <span>•</span>
            <span>Multi-Tier Knowledge Wire</span>
            <span>•</span>
            <span>AllSides Media KB</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
