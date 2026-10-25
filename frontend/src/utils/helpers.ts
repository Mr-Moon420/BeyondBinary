export function getBiasBadgeColor(bias?: string): {
  bg: string;
  text: string;
  border: string;
  dot: string;
} {
  switch (bias) {
    case 'Left':
      return {
        bg: 'bg-blue-50',
        text: 'text-blue-900',
        border: 'border-blue-200',
        dot: 'bg-blue-700',
      };
    case 'Lean Left':
      return {
        bg: 'bg-sky-50',
        text: 'text-sky-900',
        border: 'border-sky-200',
        dot: 'bg-sky-600',
      };
    case 'Center':
      return {
        bg: 'bg-stone-100',
        text: 'text-stone-800',
        border: 'border-stone-300',
        dot: 'bg-stone-600',
      };
    case 'Lean Right':
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-900',
        border: 'border-amber-200',
        dot: 'bg-amber-600',
      };
    case 'Right':
      return {
        bg: 'bg-rose-50',
        text: 'text-rose-900',
        border: 'border-rose-200',
        dot: 'bg-rose-700',
      };
    default:
      return {
        bg: 'bg-zinc-100',
        text: 'text-zinc-700',
        border: 'border-zinc-200',
        dot: 'bg-zinc-500',
      };
  }
}

export function getVerdictBadgeColor(verdict: string): {
  badge: string;
  pill: string;
  bg: string;
  text: string;
  border: string;
} {
  switch (verdict) {
    case 'Supported':
      return {
        badge: 'text-emerald-800 bg-emerald-50 border-emerald-200',
        pill: 'bg-emerald-700',
        bg: 'bg-emerald-50',
        text: 'text-emerald-900',
        border: 'border-emerald-200',
      };
    case 'Refuted':
      return {
        badge: 'text-rose-900 bg-rose-50 border-rose-200',
        pill: 'bg-rose-700',
        bg: 'bg-rose-50',
        text: 'text-rose-900',
        border: 'border-rose-200',
      };
    case 'Misleading-Framing':
      return {
        badge: 'text-amber-900 bg-amber-50 border-amber-200',
        pill: 'bg-amber-600',
        bg: 'bg-amber-50',
        text: 'text-amber-900',
        border: 'border-amber-200',
      };
    default:
      return {
        badge: 'text-zinc-700 bg-zinc-100 border-zinc-200',
        pill: 'bg-zinc-500',
        bg: 'bg-zinc-50',
        text: 'text-zinc-700',
        border: 'border-zinc-200',
      };
  }
}

export function cleanDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith('http') ? url : `https://${url}`);
    let host = parsed.hostname.toLowerCase();
    if (host.startsWith('www.')) host = host.slice(4);
    return host;
  } catch {
    return url;
  }
}
