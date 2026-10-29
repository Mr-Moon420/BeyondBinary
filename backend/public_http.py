"""Fetch public HTTP documents with pinned, validated destinations and redirects."""
import ipaddress
import socket
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter


def public_destination(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a public HTTP or HTTPS article URL without credentials.')
    if parsed.port not in (None, 80, 443):
        raise ValueError('Only standard public web ports are supported.')
    host = parsed.hostname.rstrip('.')
    if '%' in host:
        raise ValueError('Scoped network addresses are not supported.')
    addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(
        host, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(address).is_global or ipaddress.ip_address(address).is_multicast for address in addresses):
        raise ValueError('Private, loopback and local-network article URLs are not allowed.')
    addresses.sort(key=lambda address: ipaddress.ip_address(address).version != 4)
    return parsed, addresses[0]


class PublicAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        parsed, address = public_destination(request.url)
        host_params, pool_options = self.build_connection_pool_key_attributes(request, verify, cert)
        host_params['host'] = address  # No second DNS lookup can redirect this connection internally.
        if parsed.scheme == 'https':
            pool_options.update(server_hostname=parsed.hostname, assert_hostname=parsed.hostname)
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_options)

    def add_headers(self, request, **kwargs):
        request.headers['Host'] = urlsplit(request.url).netloc


def public_request(method, url, **kwargs):
    # Requests invokes the adapter again on every redirect, revalidating and pinning it.
    with requests.Session() as session:
        session.trust_env = False
        session.max_redirects = 5
        session.mount('https://', PublicAdapter())
        session.mount('http://', PublicAdapter())
        kwargs.pop('stream', None)
        with session.request(method, url, stream=True, **kwargs) as response:
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 8 * 1024 * 1024:
                    raise ValueError('Article response exceeds the 8 MB extraction limit.')
                chunks.append(chunk)
            response._content = b''.join(chunks)
            response._content_consumed = True
            return response


def public_get(url, **kwargs):
    return public_request('GET', url, **kwargs)


def public_head(url, **kwargs):
    return public_request('HEAD', url, **kwargs)
