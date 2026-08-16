from radar.site import _card


def test_untrusted_item_html_is_escaped_and_active_url_schemes_are_disabled():
    rendered = _card(
        {
            "score": 10,
            "matched_people": [],
            "matched_topics": [],
            "item": {
                "title": "<script>alert('title')</script>",
                "canonical_url": "javascript:alert('url')",
                "source": "<b>Untrusted Feed</b>",
                "published_at": "2026-08-16",
                "raw_text": "<img src=x onerror=alert('summary')>",
            },
        }
    )

    assert 'href="#"' in rendered
    assert "javascript:" not in rendered
    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;img" in rendered


def test_https_item_url_remains_clickable():
    rendered = _card(
        {
            "score": 1,
            "matched_people": [],
            "matched_topics": [],
            "item": {
                "title": "Safe item",
                "canonical_url": "https://example.org/paper?id=1&view=full",
                "source": "Example",
                "raw_text": "Summary",
            },
        }
    )

    assert 'href="https://example.org/paper?id=1&amp;view=full"' in rendered
