import pytest

from radar.collect import validate_public_url


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
