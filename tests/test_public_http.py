import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import requests
from backend.public_http import public_destination, PublicAdapter


def addresses(*values):
    return [(2, 1, 6, '', (value, 443)) for value in values]


class PublicHttpTests(unittest.TestCase):
    def test_block_private_loopback_linklocal_and_mixed_dns(self):
        for values in [('127.0.0.1',), ('10.0.0.1',), ('169.254.169.254',), ('::1',), ('93.184.216.34', '192.168.1.1')]:
            with patch('socket.getaddrinfo', return_value=addresses(*values)):
                with self.assertRaises(ValueError):
                    public_destination('https://news.example/story')

    def test_reject_credentials_schemes_and_non_web_ports_before_dns(self):
        with patch('socket.getaddrinfo') as dns:
            for url in ['file:///tmp/test', 'https://user:secret@news.example', 'https://news.example:8080/story']:
                with self.assertRaises(ValueError):
                    public_destination(url)
            dns.assert_not_called()

    def test_pin_ip_while_preserving_https_hostname_verification(self):
        adapter = PublicAdapter()
        adapter.poolmanager = MagicMock()
        prepared = requests.Request('GET', 'https://news.example/story').prepare()
        with patch('socket.getaddrinfo', return_value=addresses('93.184.216.34')):
            adapter.get_connection_with_tls_context(prepared, True)
        kwargs = adapter.poolmanager.connection_from_host.call_args.kwargs
        self.assertEqual(kwargs['host'], '93.184.216.34')
        self.assertEqual(kwargs['pool_kwargs']['server_hostname'], 'news.example')
        self.assertEqual(kwargs['pool_kwargs']['assert_hostname'], 'news.example')
        adapter.add_headers(prepared)
        self.assertEqual(prepared.headers['Host'], 'news.example')

    def test_redirect_target_is_validated_before_opening_connection(self):
        adapter = PublicAdapter()
        adapter.poolmanager = MagicMock()
        redirected = requests.Request('GET', 'http://internal.example/secret').prepare()
        with patch('socket.getaddrinfo', return_value=addresses('127.0.0.1')):
            with self.assertRaises(ValueError):
                adapter.get_connection_with_tls_context(redirected, True)
        adapter.poolmanager.connection_from_host.assert_not_called()


if __name__ == '__main__':
    unittest.main()
