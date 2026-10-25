import type {
  AnalysisResponse,
  FetchUrlResponse,
  TrendingResponse,
  CompareRequest,
  CompareResponse,
} from '../types/api';

const API_BASE_URL = '';

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchTrendingFeed(topic?: string, refresh?: boolean): Promise<TrendingResponse> {
  const params = new URLSearchParams();
  if (topic) params.append('topic', topic);
  if (refresh) params.append('refresh', 'true');
  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE_URL}/trending${query}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch trending stories (HTTP ${res.status})`);
  }

  return res.json();
}

export async function fetchArticleByUrl(url: string): Promise<FetchUrlResponse> {
  const res = await fetch(`${API_BASE_URL}/fetch-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch article from URL (HTTP ${res.status})`);
  }

  return res.json();
}

export async function analyzeArticle(payload: {
  text?: string;
  url?: string;
}): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Analysis failed (HTTP ${res.status})`);
  }

  return res.json();
}


export async function comparePerspectives(payload: CompareRequest): Promise<CompareResponse> {
  const res = await fetch(`${API_BASE_URL}/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Perspective comparison failed (HTTP ${res.status})`);
  }

  return res.json();
}
