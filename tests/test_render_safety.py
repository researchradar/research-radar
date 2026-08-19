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


def test_ranking_explanation_is_collapsed_and_lists_breakdown_and_signals():
    rendered = _card(
        {
            "score": 67,
            "score_breakdown": {
                "people": 20,
                "institutions": 5,
                "topics": 10,
                "questions": 10,
                "recency": 7,
                "source": 5,
                "evidence": 10,
                "feedback": 0,
            },
            "matched_people": ["Ada Example"],
            "matched_institutions": ["Example Lab"],
            "matched_topics": ["Robot Learning"],
            "matched_questions": ["How do robots learn safely?"],
            "item": {
                "title": "Safe robot learning",
                "canonical_url": "https://example.org/paper",
                "source": "Example",
                "raw_text": "Summary",
            },
        }
    )

    assert '<details class="explanation">' in rendered
    assert '<details class="explanation" open>' not in rendered
    assert "<summary>Why this ranked</summary>" in rendered
    assert "<dt>People</dt><dd>20</dd>" in rendered
    assert "<dt>Evidence</dt><dd>10</dd>" in rendered
    assert "<strong>People:</strong> Ada Example" in rendered
    assert "<strong>Institutions:</strong> Example Lab" in rendered
    assert "<strong>Topics:</strong> Robot Learning" in rendered
    assert "<strong>Questions:</strong> How do robots learn safely?" in rendered


def test_untrusted_ranking_explanation_content_is_escaped():
    rendered = _card(
        {
            "score": 1,
            "score_breakdown": {
                "<script>breakdown</script>": "<img src=x onerror=alert('score')>"
            },
            "matched_people": ["<svg onload=alert('person')>"],
            "matched_institutions": ["<script>alert('institution')</script>"],
            "matched_topics": ["<img src=x onerror=alert('topic')>"],
            "matched_questions": ["<iframe srcdoc='<script>alert(1)</script>'>"],
            "item": {
                "title": "Safe title",
                "canonical_url": "https://example.org/paper",
                "source": "Example",
                "raw_text": "Summary",
            },
        }
    )

    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "<svg" not in rendered
    assert "<iframe" not in rendered
    assert "&lt;Script&gt;Breakdown&lt;/Script&gt;" in rendered
    assert "&lt;img src=x onerror=alert(&#x27;score&#x27;)&gt;" in rendered
    assert "&lt;svg onload=alert(&#x27;person&#x27;)&gt;" in rendered
    assert "&lt;script&gt;alert(&#x27;institution&#x27;)&lt;/script&gt;" in rendered
    assert "&lt;img src=x onerror=alert(&#x27;topic&#x27;)&gt;" in rendered
    assert "&lt;iframe srcdoc=&#x27;&lt;script&gt;alert(1)&lt;/script&gt;&#x27;&gt;" in rendered
