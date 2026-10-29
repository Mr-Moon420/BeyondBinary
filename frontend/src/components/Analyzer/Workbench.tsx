import { useState, useEffect, useRef, type FC } from 'react';
import { AlertTriangle, CheckCircle2, FileQuestion } from 'lucide-react';
import { IngestionBar } from './IngestionBar';
import { ArticleReader } from './ArticleReader';
import { CredibilityGauge } from './CredibilityGauge';
import { SpectrumSlider } from './SpectrumSlider';
import { EchoChamberMatrix } from './EchoChamberMatrix';
import { FramingAnalytics } from './FramingAnalytics';
import { ClaimsList } from './ClaimsList';
import { AnalysisProgressStepper } from './AnalysisProgressStepper';
import type { AnalysisResponse } from '../../types/api';
import { fetchArticleByUrl, analyzeArticle } from '../../services/api';
import { cleanDomain } from '../../utils/helpers';

interface WorkbenchProps {
  initialUrl?: string;
  initialTitle?: string;
  initialSnippet?: string;
  onResetContext?: () => void;
}

export const Workbench: FC<WorkbenchProps> = ({
  initialUrl = '',
  initialTitle = '',
  onResetContext,
}) => {
  const [url, setUrl] = useState<string>(initialUrl);
  const [text, setText] = useState<string>('');
  const [inputMode, setInputMode] = useState<'url' | 'paste'>('url');
  const [articleTitle, setArticleTitle] = useState<string>(initialTitle);
  const [sourceDomain, setSourceDomain] = useState<string>('');
  const [wordCount, setWordCount] = useState<number>(0);
  const [contentKind, setContentKind] = useState('article');
  const requestVersion = useRef(0);

  const [isFetchingUrl, setIsFetchingUrl] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);

  useEffect(() => {
    if (initialUrl) {
      setAnalysisResult(null);
      if (initialUrl) setUrl(initialUrl);
      if (initialTitle) setArticleTitle(initialTitle);
      if (initialUrl) {
        handleFetchUrl(initialUrl, initialTitle);
      }
    }
  }, [initialUrl]);

  const handleFetchUrl = async (targetUrl?: string, targetTitle?: string) => {
    const urlToFetch = (targetUrl || url).trim();
    if (!urlToFetch) return;
    const version = ++requestVersion.current;
    setText('');
    setWordCount(0);

    // Reset previous analysis ledger and state immediately
    setAnalysisResult(null);
    setIsFetchingUrl(true);
    setErrorMessage(null);
    setStatusMessage('Extracting article content from outlet...');

    try {
      const titleToPass = targetTitle || articleTitle || undefined;
      const data = await fetchArticleByUrl(urlToFetch, titleToPass);
      if (version !== requestVersion.current) return;
      if (!data.success) {
        throw new Error(data.error || 'Failed to extract article content.');
      }

      setText(data.text);
      setUrl(data.url || urlToFetch);
      setContentKind(data.content_kind || 'article');
      setArticleTitle(data.title || 'Article Loaded');
      setSourceDomain(data.domain || cleanDomain(urlToFetch));
      setWordCount(data.word_count || data.text.split(/\s+/).length);
      setStatusMessage(`✓ Ingested ${data.word_count} words from ${data.domain || cleanDomain(urlToFetch)}`);
      setTimeout(() => setStatusMessage(''), 4000);
    } catch (err: any) {
      if (version !== requestVersion.current) return;
      setErrorMessage(`${err.message || 'Could not fetch article.'} You can paste the article in Raw Text Manuscript.`);
      setStatusMessage('');
    } finally {
      if (version === requestVersion.current) setIsFetchingUrl(false);
    }
  };

  const handleAnalyze = async () => {
    if (!text.trim() && !url.trim()) return;
    const version = ++requestVersion.current;

    // Clear previous article claims and dossier immediately so UI stays clean
    setAnalysisResult(null);
    setIsAnalyzing(true);
    setErrorMessage(null);
    setStatusMessage('Extracting check-worthy claims & running RoBERTa inference...');

    try {
      const result = await analyzeArticle({
        text: text.trim(),
        url: url.trim() || undefined,
        title: articleTitle || undefined,
      });
      if (version !== requestVersion.current) return;

      if (result.error) {
        throw new Error(result.error);
      }

      setAnalysisResult(result);
      if (result.title) setArticleTitle(result.title);
      if (result.source_url) setSourceDomain(cleanDomain(result.source_url));
      if (result.text && !text) setText(result.text);

      setStatusMessage(
        `✓ Audit complete: ${result.claims.length} claims verified with ${result.search_provider || 'Brave Search'}`
      );
      setTimeout(() => setStatusMessage(''), 5000);
    } catch (err: any) {
      if (version !== requestVersion.current) return;
      setErrorMessage(err.message || 'Analysis pipeline encountered an error.');
      setStatusMessage('');
    } finally {
      if (version === requestVersion.current) setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    ++requestVersion.current;
    setIsFetchingUrl(false);
    setIsAnalyzing(false);
    setContentKind('article');
    onResetContext?.();
    setUrl('');
    setText('');
    setArticleTitle('');
    setSourceDomain('');
    setWordCount(0);
    setAnalysisResult(null);
    setErrorMessage(null);
    setStatusMessage('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
      {/* Section Header */}
      <div className="pb-4 border-b border-stone-300 mb-6">
        <span className="text-[11px] font-mono-data uppercase tracking-[0.2em] text-stone-500 font-semibold block mb-1">
          Forensic Investigation
        </span>
        <h2 className="text-2xl sm:text-3xl font-editorial font-bold text-stone-900">
          Article Audit & Deconstruction Desk
        </h2>
      </div>

      {/* Top Ingestion Bar */}
      <IngestionBar
        url={url}
        onChangeUrl={(nextUrl) => { handleReset(); setUrl(nextUrl); }}
        onFetchUrl={() => handleFetchUrl()}
        isFetchingUrl={isFetchingUrl}
        inputMode={inputMode}
        onChangeMode={(mode) => {
          setInputMode(mode);
          if (mode === 'paste') {
            ++requestVersion.current;
            setIsFetchingUrl(false); setIsAnalyzing(false);
            setUrl(''); setSourceDomain(''); setArticleTitle('');
            setContentKind('article'); setAnalysisResult(null); setStatusMessage('');
            onResetContext?.();
          }
        }}
        articleMeta={{
          title: articleTitle,
          domain: sourceDomain,
          wordCount,
          contentKind,
        }}
      />

      {/* Status Bar */}
      {statusMessage && (
        <div className="p-3 bg-stone-100 border border-stone-300 rounded text-xs text-stone-800 font-mono-data mb-6 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-900 font-mono-data mb-6 flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-700 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Workbench Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-10">
        {/* Left Column: Article Manuscript (7 cols) */}
        <div className="lg:col-span-7 h-full">
          <ArticleReader
            text={text}
            onChangeText={(newText) => {
              setText(newText);
              setWordCount(newText.trim() ? newText.trim().split(/\s+/).length : 0);
              if (analysisResult) setAnalysisResult(null);
            }}
            onAnalyze={handleAnalyze}
            onReset={handleReset}
            isAnalyzing={isAnalyzing}
            claims={analysisResult?.claims || []}
            loadedWords={analysisResult?.bias_analysis?.loaded_language?.detected_words || []}
            articleTitle={articleTitle}
            sourceDomain={sourceDomain}
            sourceUrl={url}
            isFetchingUrl={isFetchingUrl}
          />
        </div>

        {/* Right Column: Credibility & Bias Dossier (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {isAnalyzing ? (
            <AnalysisProgressStepper isAnalyzing={isAnalyzing} />
          ) : analysisResult ? (
            <>
              <CredibilityGauge
                score={analysisResult.credibility_score}
                claims={analysisResult.claims}
              />

              {analysisResult.bias_analysis && (
                <SpectrumSlider bias={analysisResult.bias_analysis} />
              )}

              {analysisResult.bias_analysis?.cross_source && (
                <EchoChamberMatrix
                  crossSource={analysisResult.bias_analysis.cross_source}
                />
              )}

              {analysisResult.bias_analysis?.loaded_language && (
                <FramingAnalytics
                  loadedLanguage={analysisResult.bias_analysis.loaded_language}
                  claims={analysisResult.claims}
                />
              )}
            </>
          ) : (
            <div className="editorial-card rounded-md p-8 text-center text-stone-500 text-xs">
              <FileQuestion className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <h3 className="font-editorial text-base font-bold text-stone-800 mb-1">
                Audit Dossier Pending
              </h3>
              <p className="text-stone-500 text-xs max-w-xs mx-auto leading-relaxed">
                Provide an article URL or text on the left, then click "Deconstruct & Audit Claims" to generate the multi-dimensional credibility ledger.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Stream: Claims Fact-Check Detail List (only display when not actively running a new analysis) */}
      {!isAnalyzing && analysisResult && analysisResult.claims && (
        <div className="pt-6 border-t border-stone-300">
          <ClaimsList claims={analysisResult.claims} />
        </div>
      )}
    </div>
  );
};
