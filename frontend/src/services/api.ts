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

export async function fetchArticleByUrl(url: string, title?: string): Promise<FetchUrlResponse> {
  const res = await fetch(`${API_BASE_URL}/fetch-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ url, title }),
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch article from URL (HTTP ${res.status})`);
  }

  return res.json();
}

export async function analyzeArticle(payload: {
  text?: string;
  url?: string;
  title?: string;
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
  const res = await fetch(`${API_BASE_URL}/compare/jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => null);
    if (typeof error?.detail === 'string') throw new Error(error.detail);
    throw new Error(`Perspective comparison failed (HTTP ${res.status})`);
  }

  const { job_id } = await res.json();
  // Poll with short requests so the public proxy cannot time out the analysis.
  for (;;) {
    await new Promise(resolve => setTimeout(resolve, 1500));
    const status = await fetch(`${API_BASE_URL}/compare/jobs/${job_id}`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    const data = await status.json().catch(() => null);
    if (!status.ok) {
      throw new Error(typeof data?.detail === 'string'
        ? data.detail : `Perspective comparison failed (HTTP ${status.status})`);
    }
    if (data?.status === 'complete') return data.result;
  }
}
