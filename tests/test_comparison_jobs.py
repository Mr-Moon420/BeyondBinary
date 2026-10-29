"""Regression checks for comparisons that outlast a public HTTP request."""
import threading
import time
import unittest
import sys
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# These tests exercise HTTP/job handling, not inference. Avoid loading a second
# copy of the live server's large model/index libraries into laptop memory.
with patch.dict(sys.modules, {name: MagicMock() for name in (
    "claim_extractor", "scorer", "search_provider", "verifier",
    "bias_detector", "article_fetcher",
)}):
    from backend import main


class ComparisonJobsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        main._COMPARE_JOBS.clear()

    def test_slow_comparison_does_not_block_requests_and_preserves_result(self):
        release = threading.Event()
        expected = {"outlet_a": {"claims": ["a"]}, "outlet_b": {}, "comparison": {"score": 12}}

        def slow_comparison(request):
            release.wait(5)
            return expected

        with patch.object(main, "compare_perspectives", side_effect=slow_comparison):
            try:
                response = self.client.post("/compare/jobs", json={"text_a": "Article A", "text_b": "Article B"})
                self.assertEqual(response.status_code, 202)
                url = "/compare/jobs/" + response.json()["job_id"]
                self.assertIn(self.client.get(url).json()["status"], ["pending", "running"])
                self.assertEqual(self.client.get("/health").status_code, 200)
            finally:
                release.set()
            for _ in range(100):
                result = self.client.get(url).json()
                if result["status"] == "complete":
                    break
                time.sleep(0.01)
            self.assertEqual(result, {"status": "complete", "result": expected})

    def test_failed_and_missing_jobs_give_actionable_errors(self):
        failed = Future()
        failed.set_exception(RuntimeError("private implementation detail"))
        main._COMPARE_JOBS["failed"] = (time.monotonic(), failed)
        response = self.client.get("/compare/jobs/failed")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private implementation detail", response.text)
        self.assertEqual(self.client.get("/compare/jobs/missing").status_code, 404)

    def test_requires_both_articles_and_bounds_queue(self):
        self.assertEqual(self.client.post("/compare/jobs", json={"text_a": "A"}).status_code, 422)
        for index in range(4):
            main._COMPARE_JOBS[str(index)] = (time.monotonic(), Future())
        response = self.client.post("/compare/jobs", json={"text_a": "A", "text_b": "B"})
        self.assertEqual(response.status_code, 429)

    def test_comparison_uses_actual_lowercase_model_probabilities(self):
        left = {"bias_analysis": {"stance": {"probabilities": {"left": 1, "center": 0, "right": 0}}}}
        right = {"bias_analysis": {"stance": {"probabilities": {"Left": 0, "Center": 0, "Right": 1}}}}
        result = main._compute_echo_chamber_divergence(left, right)
        self.assertEqual(result["stance_divergence_pct"], 100)
        self.assertEqual(result["polarization_score"], 100)
        self.assertEqual(main._compute_echo_chamber_divergence(left, left)["polarization_score"], 0)

    def test_comparison_resolves_publisher_from_full_url(self):
        with patch.object(main, "extract_claims", return_value=[]), \
             patch.object(main, "analyze_bias", return_value={}), \
             patch.object(main, "compute_score", return_value=50):
            cbs = main._analyze_outlet_payload("https://www.cbsnews.com/news/example/", "Article text")
            ap = main._analyze_outlet_payload("https://www.ap.org/news/example/", "Article text")
        self.assertEqual(cbs["source_name"], "CBS News")
        self.assertEqual(ap["source_name"], "ap.org")

    def test_similar_publisher_name_does_not_borrow_rating(self):
        publisher = main._lookup_publisher('https://centredaily.com/sports/story', source_name='Centre Daily Times')
        self.assertEqual(publisher['name'], 'Centre Daily Times')
        self.assertEqual(publisher['bias'], 'Unrated')
        self.assertIsNone(publisher['score'])

    def test_failed_fetch_cannot_produce_a_consensus_score(self):
        with patch.object(main, 'fetch_article_from_url', return_value={'success': False}):
            with self.assertRaises(main.HTTPException) as failure:
                main.compare_perspectives(main.CompareRequest(url_a='https://example.org/a', url_b='https://example.org/b'))
        self.assertEqual(failure.exception.status_code, 422)

    def test_job_preserves_actionable_fetch_error(self):
        future = Future()
        future.set_exception(main.HTTPException(status_code=422, detail='Article unavailable'))
        main._COMPARE_JOBS['unavailable'] = (time.monotonic(), future)
        response = self.client.get('/compare/jobs/unavailable')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['detail'], 'Article unavailable')

    def test_oversized_text_is_rejected_before_analysis(self):
        response = self.client.post('/analyze', json={'text': 'x' * 100001})
        self.assertEqual(response.status_code, 422)

    def test_url_identity_overrides_an_incorrect_outlet_label(self):
        with patch.object(main, 'extract_claims', return_value=[]), patch.object(main, 'analyze_bias', return_value={}), patch.object(main, 'compute_score', return_value=0):
            result = main._analyze_outlet_payload('https://www.ap.org/story', 'Article text', fallback_source='The Washington Post')
        self.assertEqual(result['source_name'], 'ap.org')


if __name__ == "__main__":
    unittest.main()
