import unittest
from backend.verification_logic import aggregate, add_influence, eligibility, probabilities, trace_explanation
from backend.scorer import compute_score
from backend.xai_explainer import _extract_numbers, explain_verification


def row(identity, entailment, contradiction, neutral, eligible=True):
    return {'id': identity, 'eligible': eligible, 'sentence': 'Paris is the capital of France.',
            'source': {'title': 'Reference'}, 'probabilities': {
                'entailment': entailment, 'contradiction': contradiction, 'neutral': neutral}}


class VerificationLogicTests(unittest.TestCase):
    def test_conflicting_evidence_abstains_regardless_of_vote_counts(self):
        rows = [row('E1', .91, .02, .07), row('E2', .01, .99, 0), row('E3', .95, .01, .04)]
        verdict, confidence, reason = aggregate(rows)
        self.assertEqual(verdict, 'Not Enough Info')
        self.assertEqual(confidence, .5)
        self.assertIn('Conflicting', reason)

    def test_no_evidence_weak_evidence_and_ineligible_refutation_abstain(self):
        for rows in [[], [row('E1', .4, .4, .2)], [row('E1', .01, .98, .01, False)]]:
            self.assertEqual(aggregate(rows)[:2], ('Not Enough Info', .5))

    def test_resolved_verdicts_keep_actual_model_score(self):
        self.assertEqual(aggregate([row('E1', .95, .01, .04)])[:2], ('Supported', .95))
        self.assertEqual(aggregate([row('E1', .01, .95, .04)])[:2], ('Refuted', .95))

    def test_unrelated_subject_self_source_and_duplicates_are_ineligible(self):
        self.assertFalse(eligibility('Zorvax Laboratory measured 713 particles.', 'The Philadelphia experiment was fictional.', .8)[0])
        self.assertFalse(eligibility('Paris is the capital of France.', 'Paris is in France.', .8, same_source=True)[0])
        self.assertFalse(eligibility('Paris is the capital of France.', 'Paris is in France.', .8, duplicate=True)[0])
        self.assertFalse(eligibility('Paris is the capital of France.', 'Paris is in France.', .1)[0])
        self.assertTrue(eligibility('Apollo 11 landed in July 1989.', 'Apollo 11 landed in July 1969.', .8)[0])

    def test_probability_vectors_are_complete_and_normalized(self):
        result = probabilities([[{'label': 'ENTAILMENT', 'score': .8}, {'label': 'NEUTRAL', 'score': .1}, {'label': 'CONTRADICTION', 'score': .1}]])
        self.assertAlmostEqual(sum(result.values()), 1)
        with self.assertRaises(ValueError):
            probabilities([{'label': 'ENTAILMENT', 'score': .9}])

    def test_influence_uses_same_evidence_and_explains_counterfactual(self):
        rows = [row('E1', .95, .01, .04), row('E2', .1, .1, .8)]
        self.assertEqual(add_influence(rows), 'E1')
        self.assertTrue(rows[0]['verdict_changes_without'])
        self.assertEqual(rows[0]['without_verdict'], 'Not Enough Info')
        self.assertFalse(rows[1]['verdict_changes_without'])
        verdict, _, reason = aggregate(rows)
        explanation = trace_explanation(verdict, reason, rows)['rationale']
        self.assertIn('E1', explanation)
        self.assertIn('Paris is the capital of France.', explanation)

    def test_tone_penalty_never_increases_zero_score(self):
        self.assertEqual(compute_score([{'verdict': 'Refuted', 'confidence': .9}], loaded_density_pct=5), 0)

    def test_diagnostic_numbers_and_uncertain_dates(self):
        self.assertEqual(_extract_numbers('50% and 25%'), ['50%', '25%'])
        self.assertEqual(_extract_numbers('$1 million and $2 million'), ['$1 million', '$2 million'])
        result = explain_verification('The building opened in 2000.', 'Not Enough Info', .5, ['A town festival happened in 2020.'])
        self.assertEqual(result['conflict_diff'], [])


if __name__ == '__main__':
    unittest.main()
