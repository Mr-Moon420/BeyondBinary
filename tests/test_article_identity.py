import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.article_identity import same_article_url
from backend import article_fetcher


class ArticleIdentityTests(unittest.TestCase):
    def test_tracking_and_www_do_not_change_article(self):
        self.assertTrue(same_article_url('https://www.example.com/story/?utm_source=test', 'https://example.com/story'))
        self.assertFalse(same_article_url('https://example.com/story', 'https://example.com/story-two'))
        self.assertFalse(same_article_url('https://a.example/story', 'https://b.example/story'))
        self.assertFalse(same_article_url('', ''))

    def test_search_cannot_substitute_a_related_article(self):
        provider = SimpleNamespace(is_configured=True, search=lambda *a, **k: [
            {'url': 'https://different.example/related', 'title': 'Similar event', 'snippet': 'related facts ' * 40},
        ])
        with patch('search_provider.get_search_provider', return_value=provider), patch.object(article_fetcher, 'public_get') as get:
            result = article_fetcher._query_search_bypass('Some headline', 'https://original.example/story', 'original.example')
        self.assertIsNone(result)
        get.assert_not_called()

    def test_indexed_excerpt_stays_single_source_and_is_labelled(self):
        url = 'https://original.example/story'
        provider = SimpleNamespace(is_configured=True, search=lambda *a, **k: [
            {'url': url, 'title': 'Original headline', 'snippet': 'original words ' * 25},
            {'url': 'https://other.example/story', 'title': 'Other headline', 'snippet': 'unrelated words ' * 30},
        ])
        with patch('search_provider.get_search_provider', return_value=provider), patch.object(article_fetcher, 'public_get', return_value=SimpleNamespace(status_code=403)):
            result = article_fetcher._query_search_bypass('Original headline', url, 'original.example')
        self.assertTrue(result['success'])
        self.assertEqual(result['url'], url)
        self.assertEqual(result['content_kind'], 'indexed_excerpt')
        self.assertNotIn('unrelated', result['text'])


if __name__ == '__main__':
    unittest.main()
