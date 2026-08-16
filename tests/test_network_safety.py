import socket

import pytest

from radar.collect import safe_get, validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.org/feed.xml",
        "http://localhost/feed.xml",
        "http://127.0.0.1/feed.xml",
        "http://10.0.0.1/feed.xml",
        "http://169.254.169.254/latest/meta-data/",
        "http://user:password@example.org/feed.xml",
    ],
)
def test_private_or_unsafe_source_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def _public_dns(*args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", 443),
        )
    ]


class _FakeResponse:
    def __init__(self, *, headers=None, redirect=False, chunks=()):
        self.headers = headers or {}
        self.is_redirect = redirect
        self.is_permanent_redirect = False
        self._chunks = list(chunks)
        self.closed = False
        self._content = False
        self._content_consumed = False

    @property
    def content(self):
        return self._content

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=65536):
        yield from self._chunks

    def close(self):
        self.closed = True


def test_redirect_to_private_network_is_rejected_before_second_fetch(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    calls = []
    redirect = _FakeResponse(
        headers={"Location": "http://169.254.169.254/latest/meta-data/"},
        redirect=True,
    )

    def fake_get(self, url, **kwargs):
        calls.append(url)
        return redirect

    monkeypatch.setattr("requests.Session.get", fake_get)

    with pytest.raises(ValueError):
        safe_get("https://example.org/feed.xml")
    assert calls == ["https://example.org/feed.xml"]
    assert redirect.closed


def test_response_body_is_bounded_even_without_content_length(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    response = _FakeResponse(chunks=[b"12345", b"67890"])

    def fake_get(self, url, **kwargs):
        assert kwargs["stream"] is True
        return response

    monkeypatch.setattr("requests.Session.get", fake_get)

    with pytest.raises(ValueError, match="size limit"):
        safe_get("https://example.org/feed.xml", max_bytes=8)
    assert response.closed


def test_fetch_session_does_not_inherit_environment_credentials(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_dns)
    response = _FakeResponse(chunks=[b"ok"])

    def fake_get(self, url, **kwargs):
        assert self.trust_env is False
        return response

    monkeypatch.setattr("requests.Session.get", fake_get)
    result = safe_get("https://example.org/feed.xml", max_bytes=8)
    assert result.content == b"ok"
