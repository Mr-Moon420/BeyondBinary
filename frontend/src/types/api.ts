export interface EvidenceSource {
  title: string;
  url: string;
  snippet?: string;
  extra_snippets?: string[];
  domain?: string;
  outlet?: string;
  bias?: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right' | 'Unrated';
  score?: number | null;
  source_type?: string;
}

export interface FramingAnalysis {
  is_misleading: boolean;
  framing_type: string | null;
  detected_markers: string[];
  density_pct: number;
  explanation: string;
}

export interface XAIEntityDiff {
  type: string;
  claim_val: string;
  evidence_val: string;
}

export interface XAIRationale {
  category: string;
  rationale: string;
  conflict_diff?: XAIEntityDiff[];
  alignment_entities?: string[];
  flagged_markers?: string[];
}

export interface VerifiedClaim {
  claim: string;
  verdict: 'Supported' | 'Refuted' | 'Misleading-Framing' | 'Not Enough Info';
  confidence: number;
  evidence: string[] | string;
  sources?: EvidenceSource[];
  retrieval_source: string;
  framing_analysis?: FramingAnalysis;
  xai_rationale?: XAIRationale;
}

export interface DomainRating {
  domain: string;
  name: string;
  bias: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right' | 'Unrated';
  score?: number;
}

export interface LoadedLanguage {
  loaded_count: number;
  total_words: number;
  density_pct: number;
  loaded_words: string[];
  detected_words: string[];
}

export interface StanceAnalysis {
  probabilities: {
    Left?: number;
    Center?: number;
    Right?: number;
    left?: number;
    center?: number;
    right?: number;
  };
  stance_score: number;
  stance_label: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right';
}

export interface CrossSourceDistribution {
  distribution: {
    Left: number;
    'Lean Left': number;
    Center: number;
    'Lean Right': number;
    Right: number;
    Unrated: number;
  };
  total_sources: number;
  total_rated: number;
  sources: EvidenceSource[];
}

export interface BiasAnalysis {
  bias_label: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right';
  spectrum_score: number;
  confidence: number;
  stance: StanceAnalysis;
  domain_rating: DomainRating | null;
  loaded_language: LoadedLanguage;
  cross_source: CrossSourceDistribution | null;
}

export interface AnalysisResponse {
  title?: string;
  source_url?: string | null;
  text?: string;
  credibility_score: number;
  claims: VerifiedClaim[];
  bias_analysis: BiasAnalysis | null;
  extractor?: string;
  search_provider?: string;
  error?: string;
}

export interface TrendingPerspective {
  title: string;
  source: string;
  url?: string;
  bias?: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right' | 'Unrated';
}

export interface TrendingArticle {
  title: string;
  url: string;
  snippet?: string;
  age?: string;
  publisher: {
    name: string;
    bias: 'Left' | 'Lean Left' | 'Center' | 'Lean Right' | 'Right' | 'Unrated';
    score: number | null;
  };
  perspectives?: TrendingPerspective[];
}

export interface TrendingResponse {
  topics: {
    [category: string]: TrendingArticle[];
  };
  error?: string;
}

export interface FetchUrlResponse {
  success: boolean;
  url: string;
  domain: string;
  title: string;
  text: string;
  word_count: number;
  error?: string | null;
}

export interface CompareOutlet {
  title: string;
  source_name: string;
  source_url?: string;
  credibility_score: number;
  claims: VerifiedClaim[];
  bias_analysis: BiasAnalysis;
  word_count: number;
  summary: string;
  error?: string;
}

export interface RhetoricContrast {
  density_a: number;
  density_b: number;
  density_diff: number;
  terms_a: string[];
  terms_b: string[];
  higher_sensationalism: string;
}

export interface EchoChamberComparison {
  polarization_score: number;
  divergence_level: string;
  divergence_description: string;
  stance_divergence_pct: number;
  spectrum_delta: number;
  rhetoric_contrast: RhetoricContrast;
  editorial_synthesis: string;
}

export interface CompareResponse {
  outlet_a: CompareOutlet;
  outlet_b: CompareOutlet;
  comparison: EchoChamberComparison;
  error?: string;
}

export interface CompareRequest {
  url_a?: string;
  text_a?: string;
  title_a?: string;
  source_a?: string;
  url_b?: string;
  text_b?: string;
  title_b?: string;
  source_b?: string;
}
