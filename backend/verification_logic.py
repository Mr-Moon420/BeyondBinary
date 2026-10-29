"""Auditable evidence eligibility and aggregation; thresholds are heuristics."""
import re
import math

DECISIVE = 0.72
MIN_RELEVANCE = 0.45
_GENERIC_NAMES = set(('the a an in on at as it this that according president prime minister '
    'laboratory experiment scientists government july june january february march april may '
    'august september october november december monday tuesday wednesday thursday friday '
    'saturday sunday river reported said they we he she his her their our these those '
    'but however senior former new').split())


def probabilities(raw):
    while isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
        raw = raw[0]
    if isinstance(raw, dict) and 'probabilities' in raw:
        values = raw['probabilities']
    else:
        values = {item['label'].lower(): float(item['score']) for item in raw}
    if {str(key).lower() for key in values} != {'entailment', 'contradiction', 'neutral'}:
        raise ValueError('NLI must return all three labels')
    result = {name: float(values.get(name, values.get(name.upper(), 0)))
              for name in ('entailment', 'contradiction', 'neutral')}
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in result.values()):
        raise ValueError('Invalid NLI probability')
    total = sum(result.values())
    if total <= 0:
        raise ValueError('NLI returned no three-way probabilities')
    return {name: value / total for name, value in result.items()}


def eligibility(claim, evidence, similarity, same_source=False, duplicate=False):
    if same_source:
        return False, 'This is the article being audited; it cannot independently corroborate itself.'
    if duplicate:
        return False, 'Duplicate evidence text or source URL; not an additional corroboration.'
    if similarity < MIN_RELEVANCE:
        return False, 'Retrieved passage is weakly related to this claim.'
    names = [name.lower() for name in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', claim)
             if name.lower() not in _GENERIC_NAMES]
    evidence_words = set(re.findall(r'[a-z]+', evidence.lower()))
    if names and not any(name in evidence_words for name in names):
        return False, 'The passage does not identify the claim\'s named subject.'
    if evidence.rstrip().endswith('?'):
        return False, 'A retrieved question does not establish the asserted fact.'
    return True, 'Related passage with a matching subject; eligible for NLI aggregation.'


def aggregate(rows):
    usable = [row for row in rows if row.get('eligible') and row.get('probabilities')]
    support = [row for row in usable if row['probabilities']['entailment'] >= DECISIVE]
    oppose = [row for row in usable if row['probabilities']['contradiction'] >= DECISIVE]
    if support and oppose:
        return 'Not Enough Info', 0.5, 'Conflicting evidence: eligible passages both support and contradict this claim.'
    if support:
        return 'Supported', round(sum(r['probabilities']['entailment'] for r in support) / len(support), 3), 'Eligible evidence supports the claim.'
    if oppose:
        return 'Refuted', round(sum(r['probabilities']['contradiction'] for r in oppose) / len(oppose), 3), 'Eligible evidence contradicts the claim.'
    return 'Not Enough Info', 0.5, 'No eligible passage decisively supports or contradicts the claim.'


def support_margin(rows):
    usable = [row for row in rows if row.get('eligible') and row.get('probabilities')]
    return sum(r['probabilities']['entailment'] - r['probabilities']['contradiction'] for r in usable) / len(usable) if usable else 0.0


def add_influence(rows):
    verdict = aggregate(rows)[0]
    margin = support_margin(rows)
    for row in rows:
        remainder = [other for other in rows if other is not row]
        row['without_verdict'] = aggregate(remainder)[0]
        row['verdict_changes_without'] = row['without_verdict'] != verdict
        row['support_margin_change'] = round(margin - support_margin(remainder), 4)
    eligible = [row for row in rows if row.get('eligible') and row.get('probabilities')]
    return max(eligible, key=lambda r: (r['verdict_changes_without'], abs(r['support_margin_change'])))['id'] if eligible else None


def trace_explanation(verdict, reason, rows):
    decisive = 'entailment' if verdict == 'Supported' else 'contradiction'
    matches = [r for r in rows if r.get('eligible') and r.get('probabilities')
               and r['probabilities'][decisive] >= DECISIVE]
    if verdict == 'Not Enough Info':
        references = ', '.join(r['id'] for r in rows if r.get('eligible'))
        rationale = reason + (f' See {references}.' if references else ' Retrieved material is shown below, with the eligibility reasons.')
        category = 'Conflicting Evidence' if reason.startswith('Conflicting') else 'Insufficient Evidence Grounding'
    else:
        selected = max(matches, key=lambda r: r['probabilities'][decisive])
        quote = selected['sentence'][:260]
        rationale = f"{reason} Evidence {selected['id']} ({selected['source'].get('title') or 'retrieved passage'}) states: \"{quote}\". The NLI {decisive} score is {selected['probabilities'][decisive]:.1%}; this is a model score, not calibrated factual accuracy."
        category = 'Evidence Support' if verdict == 'Supported' else 'Evidence Contradiction'
    return {'category': category, 'rationale': rationale, 'conflict_diff': [],
            'alignment_entities': [], 'flagged_markers': []}
