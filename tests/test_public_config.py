from radar.models import RawItem
from radar.ranking import rank


def test_public_mapping_config_ranks_people_and_topics():
    config = {
        "people": {
            "people": [
                {
                    "name": "Example Researcher",
                    "aliases": [],
                    "priority": 1.0,
                }
            ]
        },
        "topics": {
            "topics": {
                "embodied_ai": {
                    "label": "Embodied AI",
                    "keywords": ["robot manipulation", "world model"],
                    "priority": 1.0,
                }
            }
        },
        "scoring": {
            "scoring": {
                "followed_person_bonus": 20,
                "topic_match_bonus": 10,
                "recency_weight": 0,
            }
        },
        "feedback": {"feedback": []},
    }
    item = RawItem(
        id="example",
        canonical_url="https://example.org/item",
        title="World Models for Robot Manipulation",
        source="Example Source",
        source_type="paper",
        authors_or_guests=["Example Researcher"],
        raw_text="A robot manipulation benchmark using a world model.",
    )

    result = rank([item], config)
    assert result[0].matched_people == ["Example Researcher"]
    assert result[0].matched_topics == ["Embodied AI"]
    assert result[0].score_breakdown["people"] == 20
    assert result[0].score_breakdown["topics"] == 10
